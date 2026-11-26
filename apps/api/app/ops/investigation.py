from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langsmith import tracing_context

from .brief import brief

INPUT_LABELS = {"text": "Nội dung tin nhắn", "image": "Ảnh", "receipt": "Biên lai",
                "qr": "QR", "audio": "Ghi âm", "url": "Liên kết"}
ENTITY_LABELS = {"URL": "Tên miền", "ACCOUNT": "Tài khoản đã ẩn danh", "PHONE": "Số điện thoại đã ẩn danh"}


class WorkspaceState(TypedDict, total=False):
    campaign: dict
    inputs: dict
    connections: dict
    related: list
    media_evidence: dict
    source_counts: dict
    permission: str
    detection: dict
    threat_intel: dict
    forensics: dict
    investigation: dict
    protection: dict
    report: dict


def supervisor(_state):
    return {"permission": "draft_only"}


def detection(state):
    campaign = state["campaign"]
    return {"detection": {"risk": campaign["risk"], "group": campaign["group"], "signals": campaign["signals"],
                          "source_counts": state["source_counts"]}}


def threat_intel(state):
    confirmed = [item["id"] for item in state["related"] if item["state"] == "approved"]
    return {"threat_intel": {"confirmed_related_campaigns": confirmed,
                             "safe_browsing_hits": state["source_counts"].get("safe_browsing", 0)}}


def forensics(state):
    media = {key: count for key, count in state["inputs"].items() if key in {"receipt", "image", "audio"}}
    return {"forensics": {"reviewed_input_counts": media, "ocr_regions": state["media_evidence"].get("ocr_regions", 0),
                          "jpeg_regions": state["media_evidence"].get("jpeg_regions", 0), "transaction_status": "unverified"}}


def investigation(state):
    campaign = state["campaign"]
    nodes = [{"id": "campaign", "label": "Chiến dịch", "count": None},
             {"id": "reports", "label": "Báo cáo", "count": campaign["report_count"]}]
    for kind, count in campaign["entities"].items():
        nodes.append({"id": f"entity-{kind}", "label": ENTITY_LABELS.get(kind, "Thực thể đã ẩn danh"), "count": count})
    for kind, count in sorted(state["inputs"].items()):
        if kind in INPUT_LABELS:
            nodes.append({"id": f"input-{kind}", "label": INPUT_LABELS[kind], "count": count})
    edges = [{"from": "campaign", "to": item["id"], "count": item["count"]} for item in nodes[1:]]
    node_ids = {item["id"] for item in nodes}
    for (kind, modality), count in sorted(state["connections"].items()):
        source, target = f"entity-{kind}", f"input-{modality}"
        if source in node_ids and target in node_ids:
            edges.append({"from": source, "to": target, "count": count})
    return {"investigation": {"nodes": nodes, "edges": edges, "related_campaigns": state["related"]}}


def protection(state):
    case = state["campaign"]
    actions = ["Đối chiếu từng bằng chứng và mở kênh chính thức để xác minh người nhận."]
    if case["risk"] in {"high", "medium"}:
        actions.insert(0, "Đề nghị người dùng tạm dừng trước khi chuyển tiền.")
    if state["forensics"]["reviewed_input_counts"].get("receipt"):
        actions.append("Đối chiếu biên lai với lịch sử giao dịch từ ngân hàng.")
    return {"protection": {"recommendations": actions}}


def report(state):
    draft = brief(state["campaign"])
    return {"report": {**draft, "status": "draft", "approval_required": True,
                       "recommendation": state["protection"]["recommendations"][0]}}


NODES = (supervisor, detection, threat_intel, forensics, investigation, protection, report)
builder = StateGraph(WorkspaceState)
for node in NODES:
    builder.add_node(node.__name__, node)
builder.add_edge(START, "supervisor")
builder.add_edge("supervisor", "detection")
for node in (threat_intel, forensics, investigation):
    builder.add_edge("detection", node.__name__)
builder.add_edge(["threat_intel", "forensics", "investigation"], "protection")
builder.add_edge("protection", "report")
builder.add_edge("report", END)
workspace = builder.compile()


def run_workspace(campaign, evidence):
    snapshot = {key: campaign[key] for key in ("risk", "group", "signals", "entities", "report_count")}
    with tracing_context(enabled=False):
        result = workspace.invoke({"campaign": snapshot, **evidence})
    return {"permission": result["permission"], **{node.__name__: result[node.__name__] for node in NODES[1:]}}
