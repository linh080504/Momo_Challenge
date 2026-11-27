import json
import re

import httpx

from ...config import ROOT
from ...kit import pii_mask

PROMPT = (ROOT / "prompts" / "analyzer_signals_v1.md").read_text(encoding="utf-8")
V0 = (ROOT / "prompts" / "analyzer_v0.md").read_text(encoding="utf-8")
TAXONOMY = V0.split("TAXONOMY RÚT GỌN", 1)[1].split("YÊU CẦU ĐẦU RA", 1)[0]
SCENARIOS = frozenset(re.findall(r"^  (G[1-5]\.\d+) ", TAXONOMY, re.M))
RISK = {"high": 80, "medium": 50, "uncertain": 30, "low": 15}
PROMPT_VERSION = "signals-v8"
QWEN_MODEL = "qwen4-max"
QWEN_RESPONSES_URL = "https://ap-southeast-1.maas.qwencloudapi.com/compatible-mode/v1/responses"
INSTRUCTIONS = PROMPT.replace("{{taxonomy}}", TAXONOMY)
WEBSITE_EXPLANATION = (ROOT / "prompts" / "website_explanation_v1.md").read_text(encoding="utf-8")
JSON_FENCE = re.compile(r"```(?:json)?[ \t]*\r?\n(.*?)\r?\n```", re.IGNORECASE | re.DOTALL)
PUBLIC_LINK = re.compile(r"https?://|www\.|[\w-]+\.(?:vn|com|net|org|io)\b", re.I)
PAGE_PURPOSES = {
    "news": "tin tức hoặc thông tin thời sự",
    "project_profile": "giới thiệu một dự án, chương trình hoặc tổ chức",
    "education": "hướng dẫn hoặc phổ biến kiến thức",
    "store": "giới thiệu hoặc bán sản phẩm, dịch vụ",
    "account": "đăng nhập, đăng ký hoặc quản lý tài khoản",
}


def _qwen_output(instructions, facts_json, key, timeout, max_output_tokens):
    response = httpx.post(
        QWEN_RESPONSES_URL,
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": QWEN_MODEL,
            "instructions": instructions,
            "input": facts_json,
            "max_output_tokens": max_output_tokens,
            "reasoning": {"effort": "none"},
            "store": False,
        },
        timeout=timeout, follow_redirects=False, trust_env=False,
    )
    response.raise_for_status()
    return "".join(
        part["text"]
        for item in response.json()["output"] if item["type"] == "message"
        for part in item["content"] if part["type"] == "output_text"
    )


def query_qwen(settings, limits, instructions, facts, *, timeout=3.2, max_output_tokens=200):
    key = settings.dashscope_api_key.get_secret_value().strip()
    if not key:
        return None, "disabled"
    if not limits.take("llm-daily", settings.llm_calls_per_day, 86400):
        return None, "quota"
    try:
        output = _qwen_output(instructions, json.dumps(facts, ensure_ascii=False), key, timeout, max_output_tokens)
        fenced = JSON_FENCE.fullmatch(output.strip())
        if fenced:
            output = fenced[1]
        return json.loads(output), "ok"
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return None, "unavailable"


def _website_notes(content, public, options):
    excerpts = public.get("public_excerpts", [])
    notes = []
    used = set()
    paragraphs = content.get("content_analysis")
    if isinstance(paragraphs, list):
        for part in paragraphs[:3]:
            if not isinstance(part, dict):
                continue
            index, raw = part.get("excerpt_index"), part.get("text")
            if type(index) is not int or index in used or not 0 <= index < len(excerpts) or not isinstance(raw, str):
                continue
            text = " ".join(raw.split())
            excerpt = excerpts[index]
            if not 40 <= len(text) <= 380 or PUBLIC_LINK.search(text) or re.search(r"[0-9]|\bHTML\b", text, re.I):
                continue
            used.add(index)
            labels = ("Nội dung trang chủ", "Tin hoặc mục đáng chú ý", "Ngữ cảnh khác") if public.get("homepage") else (
                "Nội dung bài", "Chi tiết đáng chú ý", "Thông điệp hoặc hành động",
            )
            label = labels[len(notes)]
            notes.append({"label": label, "kind": "article",
                          "finding": pii_mask.mask_text(text)["masked"], "support": excerpt})

    purpose = content.get("page_purpose")
    title = public.get("public_title")
    if not notes and title and isinstance(purpose, str) and purpose in PAGE_PURPOSES:
        notes.append({"label": "Nội dung chính", "kind": "article",
                      "finding": f"Qwen nhận diện nội dung {PAGE_PURPOSES[purpose]} trong trang “{title}”."})

    ids = content.get("reason_ids")
    selected = [item for item in ids if isinstance(item, str) and item in options] if isinstance(ids, list) else []
    direct_content = ("gambling_offer", "payment_incentive", "payment_pressure")
    content_keys = dict.fromkeys([*direct_content, *selected])
    content_notes = [options[key] for key in content_keys if options.get(key, {}).get("kind") == "article"]
    notes.extend(content_notes[:4 - len(notes)])

    # Keep direct matches and risk signals visible even if the model omits them.
    primary = [key for key in ("alerts", "domain") if key in options and (key == "alerts" or options[key].get("source_url"))]
    show_gap = content.get("risk_level") == "uncertain" and "source_gap" in options
    critical = ("sensitive_form", "routing", "redirect", "account_request", "subdomain")
    keys = dict.fromkeys([*primary, *critical, *selected, "domain", "form_absence"])
    findings = [options[key] for key in keys if key in options and options[key].get("kind") != "article"
                and (key != "source_gap" or not show_gap)]
    findings = findings[:8 - len(notes) - int(show_gap)]
    if show_gap:
        findings.append(options["source_gap"])
    if not findings or len(findings) + len(notes) < 2:
        return []
    alert = findings.pop(0) if primary and primary[0] == "alerts" else None
    if alert:
        return [alert, *notes, *findings]
    return [*notes, *findings]


def infer(matches, evidence, benign, settings, limits, guidance=(), website_context=None, explanation_options=None):
    facts = {
        "signals": [rule.finding for rule, _ in matches],
        "verified_sources": [
            {"source": item["source"], "weight": item["weight"]} for item in evidence
        ],
        "familiar_benign_pattern": benign,
        "reference_guidance": list(guidance),
    }
    if website_context is not None:
        facts["website_context"] = website_context
    instructions = INSTRUCTIONS
    if explanation_options:
        facts["explanation_options"] = {key: item["finding"] for key, item in explanation_options.items()}
        instructions += "\n" + WEBSITE_EXPLANATION
    content, _ = query_qwen(settings, limits, instructions, facts, timeout=12.0 if explanation_options else 3.2,
                            max_output_tokens=900 if explanation_options else 200)
    if isinstance(content, dict) and "scenario_id" in content:
        risk, scenario = content.get("risk_level"), content["scenario_id"]
        if isinstance(risk, str) and risk in RISK and (scenario is None or isinstance(scenario, str) and scenario in SCENARIOS):
            explanation = _website_notes(content, (website_context or {}).get("public_html", {}),
                                         explanation_options) if explanation_options else []
            return QWEN_MODEL, risk, scenario, explanation
    return None
