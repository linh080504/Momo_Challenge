from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from langsmith import tracing_context

from ..auth.security import Limits
from ..config import Settings
from .brief import brief
from .qwen_review import suggest

INPUT_LABELS = {"text": "Nội dung tin nhắn", "image": "Ảnh", "receipt": "Biên lai",
                "qr": "QR", "audio": "Ghi âm", "url": "Liên kết"}
ENTITY_LABELS = {"URL": "Tên miền", "ACCOUNT": "Tài khoản đã ẩn danh", "PHONE": "Số điện thoại đã ẩn danh"}
SOURCE_NAMES = ("internal_blacklist", "external_blacklist", "safe_browsing", "domain_check", "rdap", "rules", "vietqr", "document")


class WorkspaceContext(TypedDict):
    settings: Settings
    limits: Limits


class WorkspaceState(TypedDict, total=False):
    campaign: dict
    inputs: dict
    connections: dict
    connection_times: dict
    related: list
    media_evidence: dict
    source_counts: dict
    permission: str
    supervisor_review: dict
    detection: dict
    threat_intel: dict
    forensics: dict
    investigation: dict
    protection: dict
    report: dict


def supervisor(state, runtime: Runtime[WorkspaceContext]):
    campaign = state["campaign"]
    review = suggest(runtime.context, "supervisor", "Chọn ưu tiên để chuyên viên bắt đầu rà hồ sơ.",
                     {"risk": campaign["risk"], "report_count": campaign["report_count"]}, {
                         "review_priority": "Ưu tiên đối chiếu các bằng chứng đã ghi nhận.",
                         "gather_context": "Bổ sung ngữ cảnh trước khi đề xuất cảnh báo.",
                     })
    return {"permission": "draft_only", "supervisor_review": review}


def detection(state, runtime: Runtime[WorkspaceContext]):
    campaign = state["campaign"]
    counts = {name: state["source_counts"][name] for name in SOURCE_NAMES if name in state["source_counts"]}
    review = suggest(runtime.context, "detection", "Chọn điểm đầu tiên để đối chiếu khi rà phân loại rủi ro.",
                     {"risk": campaign["risk"], "group": campaign["group"], "source_counts": counts}, {
                         "verify_source": "Ưu tiên xác minh tín hiệu với nguồn đối chiếu gốc.",
                         "verify_context": "Đọc đủ ngữ cảnh và kiểm tra nhóm thủ đoạn trước khi chốt.",
                     })
    return {"detection": {"risk": campaign["risk"], "group": campaign["group"], "signals": campaign["signals"],
                          "source_counts": state["source_counts"], "review": review}}


def threat_intel(state, runtime: Runtime[WorkspaceContext]):
    confirmed = [item["id"] for item in state["related"] if item["state"] == "approved"]
    safe_browsing_hits = state["source_counts"].get("safe_browsing", 0)
    review = suggest(runtime.context, "threat_intel", "Chọn phép đối chiếu tình báo phù hợp với các kết quả đã lưu.",
                     {"approved_related_count": len(confirmed), "safe_browsing_hits": safe_browsing_hits}, {
                         "inspect_matches": "Xem chi tiết kết quả đối chiếu và phạm vi của từng nguồn.",
                         "gather_intel": "Tìm thêm nguồn đối chiếu đã xác minh.",
                     })
    return {"threat_intel": {"confirmed_related_campaigns": confirmed,
                             "safe_browsing_hits": safe_browsing_hits, "review": review}}


def forensics(state, runtime: Runtime[WorkspaceContext]):
    media = {key: count for key, count in state["inputs"].items() if key in {"receipt", "image", "audio"}}
    facts = {"reviewed_input_counts": media, "ocr_regions": state["media_evidence"].get("ocr_regions", 0),
             "jpeg_regions": state["media_evidence"].get("jpeg_regions", 0), "transaction_status": "unverified"}
    review = suggest(runtime.context, "forensics", "Chọn bước kiểm chứng tiếp theo dựa trên các loại tệp và vùng đã ghi nhận.",
                     facts, {
                         "review_regions": "Đối chiếu các vùng chữ hoặc vùng nén với ảnh gốc khi có quyền xem.",
                         "gather_media": "Thu thập tệp nguồn được phép dùng để kiểm chứng.",
                         "verify_payment": "Đối chiếu trạng thái giao dịch qua nguồn ngân hàng đã được cấp quyền.",
                     })
    return {"forensics": {**facts, "review": review}}


def investigation(state, runtime: Runtime[WorkspaceContext]):
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
            edges.append({"from": source, "to": target, "count": count, "source": "report_cooccurrence",
                          "last_seen": state.get("connection_times", {}).get((kind, modality))})
    facts = {"report_count": campaign["report_count"], "edge_count": len(edges),
             "related_shared_entities": [item["shared_entities"] for item in state["related"]]}
    review = suggest(runtime.context, "investigation", "Chọn điểm cần kiểm chứng khi xem liên kết giữa các báo cáo.", facts, {
        "review_connections": "Rà lại bằng chứng chung trước khi đề xuất gộp hồ sơ.",
        "collect_connections": "Tìm thêm thực thể hoặc báo cáo liên quan có thể kiểm chứng.",
    })
    return {"investigation": {"nodes": nodes, "edges": edges, "related_campaigns": state["related"], "review": review}}


def protection(state, runtime: Runtime[WorkspaceContext]):
    case = state["campaign"]
    actions = ["Đối chiếu từng bằng chứng và mở kênh chính thức để xác minh người nhận."]
    if case["risk"] in {"high", "medium"}:
        actions.insert(0, "Đề nghị người dùng tạm dừng trước khi chuyển tiền.")
    if state["forensics"]["reviewed_input_counts"].get("receipt"):
        actions.append("Đối chiếu biên lai với lịch sử giao dịch từ ngân hàng.")
    review = suggest(runtime.context, "protection", "Chọn lời khuyên kiểm chứng cho chuyên viên cân nhắc.",
                     {"risk": case["risk"], "receipts": state["forensics"]["reviewed_input_counts"].get("receipt", 0)},
                     {"pause": "Cân nhắc nhắc người dùng tạm dừng chuyển tiền để kiểm tra.",
                      "check_official_channel": "Cân nhắc hướng dẫn người dùng kiểm tra qua kênh chính thức."})
    return {"protection": {"recommendations": actions, "review": review}}


def report(state, runtime: Runtime[WorkspaceContext]):
    draft = brief(state["campaign"])
    facts = {"risk": state["campaign"]["risk"], "report_count": state["campaign"]["report_count"],
             "signal_count": len(state["campaign"]["signals"])}
    review = suggest(runtime.context, "report", "Chọn nội dung chuyên viên cần kiểm tra trong bản nháp.", facts, {
        "cite_evidence": "Đối chiếu từng nhận định với bằng chứng trước khi duyệt bản nháp.",
        "state_limitations": "Ghi rõ phần nào trong hồ sơ còn cần người dùng xác minh.",
    })
    return {"report": {**draft, "status": "draft", "approval_required": True,
                       "recommendation": state["protection"]["recommendations"][0], "review": review}}


NODES = (supervisor, detection, threat_intel, forensics, investigation, protection, report)
builder = StateGraph(WorkspaceState, context_schema=WorkspaceContext)
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


def run_workspace(campaign, evidence, settings, limits):
    snapshot = {key: campaign[key] for key in ("risk", "group", "signals", "entities", "report_count")}
    with tracing_context(enabled=False):
        result = workspace.invoke({"campaign": snapshot, **evidence}, context={"settings": settings, "limits": limits})
    return {"permission": result["permission"], "supervisor_review": result["supervisor_review"],
            **{node.__name__: result[node.__name__] for node in NODES[1:]}}
