"""Analyzer pipeline (scam-analyzer SKILL.md, 6 steps).

1 read (vision OCR, if a provider is configured) -> 2 entities (code) -> 3 mask (pii) ->
4 evidence (parallel, per-tool timeout) -> 5 LLM reasoning (masked text only; validate; retry once;
fallback model) -> 6 hybrid score + post-checks (verbatim quotes, schema validation).

No LLM configured / LLM failed = "chế độ hạn chế": rules + blocklist; below medium -> "uncertain", never "low".
Total time budget: ANALYZER_TIMEOUT_S (default 8 s). Never logs raw or masked user text.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time

from . import postcheck, prompts, rules, schema, scoring
from .evidence import EvidenceItem, extract_urls, gather_evidence
from .pii import Masker, display
from .providers import ImagePart, LLMProvider, LLMRequest, ProviderError
from .text import nfc

log = logging.getLogger("app.analyzer")

AI_DISCLAIMER = ("Kết quả do AI phân tích và có thể sai. "
                 "Hãy xác minh qua số tổng đài chính thức trước khi chuyển tiền.")
LOW_SUMMARY = "Chưa thấy dấu hiệu lừa đảo, nhưng hãy xác minh qua kênh chính thức trước khi chuyển tiền."
NO_TEXT_MARK = "[KHÔNG CÓ CHỮ]"
SAFETY_MARGIN_S = 0.3
MIN_LLM_BUDGET_S = 0.8

GROUP_NAMES = {"G1": "mạo danh cơ quan, tổ chức", "G2": "mạo danh người quen", "G3": "lừa đầu tư, tuyển dụng",
               "G4": "lừa mua bán online", "G5": "lừa lấy thông tin, chiếm tài khoản"}
QUESTIONS = {
    "G1": ["Cơ quan nhà nước có bao giờ làm việc qua Zalo và nhận tiền vào tài khoản cá nhân không?",
           "Bạn đã gọi lại số tổng đài in trên website chính thức chưa?"],
    "G1.7": ["Bạn đã gọi thẳng số của khoa (bệnh viện) hoặc phòng đào tạo (trường) lấy từ website chính thức chưa?",
             "Bạn đã gọi trực tiếp cho người thân để hỏi chưa?"],
    "G2": ["Bạn đã gọi lại số cũ đã lưu của người đó chưa?", "Bạn đã hỏi một chuyện chỉ hai người biết chưa?"],
    "G3": ["Có công ty nào trả tiền để bạn nạp tiền trước không?", "Sàn này có giấy phép hoạt động ở Việt Nam không?"],
    "G4": ["Tiền đã về tài khoản thật chưa (xem trong app ngân hàng, không xem ảnh)?",
           "Tên chủ tài khoản có khớp tên shop không?"],
    "G5": ["Ngân hàng không bao giờ xin OTP. Bạn có đang bị xin OTP không?",
           "Tên miền trong link có đúng là trang chính thức không?"],
    None: ["Bạn đã gọi lại số tổng đài in trên website chính thức chưa?",
           "Bạn đã hỏi người thân trước khi chuyển tiền chưa?"],
}
BANK_NAMES = ["Vietcombank", "VietinBank", "BIDV", "Agribank", "Techcombank", "MB Bank", "MBBank", "TPBank",
              "VPBank", "ACB", "Sacombank", "HDBank", "SHB", "VIB", "SeABank", "MSB", "OCB", "Eximbank", "MoMo",
              "ZaloPay", "VNPAY"]
_BANK_RE = re.compile(r"\b(" + "|".join(re.escape(b) for b in BANK_NAMES) + r")\b", re.IGNORECASE)
_AMOUNT_RE = re.compile(r"(?<![\d.,])(\d{1,3}(?:[.,]\d{3})+ ?(?:đ|vnđ|vnd|đồng)?|\d+(?:[.,]\d+)? ?(?:triệu|tr|k|nghìn|ngàn)\b)",
                        re.IGNORECASE)


def total_timeout_s() -> float:
    try:
        return min(8.0, float(os.environ.get("ANALYZER_TIMEOUT_S", "8")))
    except ValueError:
        return 8.0


class _Clock:
    def __init__(self, budget_s: float) -> None:
        self.t0 = time.monotonic()
        self.deadline = self.t0 + budget_s

    def remaining(self) -> float:
        return self.deadline - time.monotonic() - SAFETY_MARGIN_S

    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self.t0) * 1000)


# ---- step 1: read image ----------------------------------------------------------------------

async def _ocr(image: bytes, mime: str, providers: list[LLMProvider], clock: _Clock) -> str | None:
    vision = [p for p in providers if p.supports_vision]
    if not vision:
        return None
    p = prompts.load(prompts.OCR_PROMPT)
    system, user = p.render()
    req = LLMRequest(system=system, user=user, images=(ImagePart(image, mime),), purpose="ocr",
                     temperature=0.0, max_tokens=1500, json_mode=False)
    for provider in vision:
        budget = clock.remaining() * 0.5
        if budget < MIN_LLM_BUDGET_S:
            break
        try:
            resp = await asyncio.wait_for(provider.generate(req, timeout_s=budget), timeout=budget)
            return nfc(resp.text).strip()
        except (ProviderError, asyncio.TimeoutError) as exc:
            log.warning("ocr failed", extra={"provider": repr(provider), "error": type(exc).__name__})
        except Exception as exc:  # vendor bug must not break the request
            log.error("ocr crashed", extra={"provider": repr(provider), "error": type(exc).__name__})
    return None


# ---- step 5: LLM reasoning -------------------------------------------------------------------

def _parse_json(text: str):
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    start, end = t.find("{"), t.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object")
    return json.loads(t[start:end + 1])


def _prepare_llm_output(obj, model: str, version: str) -> tuple[dict | None, list[str]]:
    if not isinstance(obj, dict):
        return None, ["(root): not an object"]
    obj = dict(obj)
    obj.update(ai_disclaimer=AI_DISCLAIMER, model=model, prompt_version=version, latency_ms=0)
    errs = schema.errors(obj)
    return (obj, []) if not errs else (None, errs)


async def _reason(masked: str, evidence_for_prompt: list[dict], providers: list[LLMProvider],
                  clock: _Clock) -> tuple[dict | None, str | None]:
    """Validated LLM dict (or None) + model name. Validation error -> retry once; provider error -> fallback."""
    if not providers:
        return None, None
    p = prompts.load(prompts.ANALYZER_PROMPT)
    system, user = p.render(
        analysis_schema=json.dumps(schema.schema(), ensure_ascii=False),
        channel="không rõ",
        masked_text=prompts.neutralize(masked),
        evidence_json=json.dumps(evidence_for_prompt, ensure_ascii=False),
    )
    feedback = ""
    for attempt in range(2):  # first try + 1 retry after a validation error
        req = LLMRequest(system=system, user=user + feedback, purpose="reason", temperature=0.1)
        validation_failed = False
        for provider in providers:
            budget = clock.remaining()
            if budget < MIN_LLM_BUDGET_S:
                log.warning("llm skipped: no time budget left", extra={"attempt": attempt})
                return None, None
            try:
                resp = await asyncio.wait_for(provider.generate(req, timeout_s=budget), timeout=budget)
            except (ProviderError, asyncio.TimeoutError) as exc:
                log.warning("llm call failed, trying fallback",
                            extra={"provider": repr(provider), "error": type(exc).__name__})
                continue
            except Exception as exc:
                log.error("llm provider crashed", extra={"provider": repr(provider), "error": type(exc).__name__})
                continue
            try:
                out, errs = _prepare_llm_output(_parse_json(resp.text), resp.model, p.version)
            except (ValueError, json.JSONDecodeError):
                out, errs = None, ["(root): không phải JSON hợp lệ"]
            if out is not None:
                return out, resp.model
            log.warning("llm output invalid", extra={"attempt": attempt, "n_errors": len(errs)})
            feedback = ("\n\nLần trả lời trước KHÔNG hợp lệ theo schema: " + "; ".join(errs[:5]) +
                        "\nHãy trả lại đúng một JSON theo schema, không thêm chữ nào khác.")
            validation_failed = True
            break
        if not validation_failed:
            return None, None  # every provider failed: no point retrying
    return None, None


# ---- step 2: entities ------------------------------------------------------------------------

def _entities(masker: Masker, urls, source: str) -> list[dict]:
    out = []
    for tok, val in masker.mapping.items():
        kind = tok.strip("[]").rsplit("_", 1)[0]
        if kind in ("ACCOUNT", "PHONE", "EMAIL", "CARD"):
            out.append({"type": kind, "token": tok, "display": display(kind, val)})
    out += [{"type": "URL", "display": u.host} for u in urls]
    seen = set()
    for m in _BANK_RE.finditer(source):
        name = m.group(1)
        if name.lower() not in seen:
            seen.add(name.lower())
            out.append({"type": "BANK", "display": name})
    for m in list(_AMOUNT_RE.finditer(source))[:3]:
        out.append({"type": "AMOUNT", "display": m.group(1).strip()})
    return out[:15]


# ---- step 6: assemble ------------------------------------------------------------------------

def _summary(level: str, group: str | None, reason: str | None = None) -> str:
    kind = f" kiểu {GROUP_NAMES[group]}" if group in GROUP_NAMES else ""
    if level == "high":
        s = f"Tin này có nhiều dấu hiệu lừa đảo{kind}. Đừng chuyển tiền. Hãy gọi lại số tổng đài chính thức để kiểm tra."
    elif level == "medium":
        s = f"Tin này có dấu hiệu đáng ngờ{kind}. Hãy dừng lại và kiểm tra qua kênh chính thức trước khi chuyển tiền."
    elif level == "uncertain":
        s = reason or ("Chưa đủ thông tin để kết luận. Đừng chuyển tiền khi chưa gọi lại số tổng đài chính thức "
                       "hoặc hỏi người thân.")
    else:
        s = LOW_SUMMARY
    return s[:280]


def _overlaps(a: str, b: str) -> bool:
    return a in b or b in a


def _merge_flags(llm_flags: list[dict], rule_signals: list[rules.Signal], level: str) -> list[dict]:
    flags: list[dict] = list(llm_flags)
    if level != "low":
        for s in sorted(rule_signals, key=lambda s: -s.points):
            if not s.quote or any(_overlaps(s.quote, f["quote"]) for f in flags):
                continue
            flags.append({"quote": s.quote, "reason": s.reason, "tactic": s.tactic})
    return flags[:5]


def _build(*, level: str, score: int, group: str | None, scenario_id: str | None, summary: str,
           flags: list[dict], questions: list[str], action: str, entities: list[dict], evidence: list[dict],
           model: str, prompt_version: str, latency_ms: int) -> dict:
    return {"risk_level": level, "risk_score": int(score), "scenario_group": group, "scenario_id": scenario_id,
            "summary": summary[:280], "red_flags": flags[:5], "verification_questions": questions[:3],
            "recommended_action": action, "entities": entities, "evidence": evidence,
            "ai_disclaimer": AI_DISCLAIMER, "model": model, "prompt_version": prompt_version,
            "latency_ms": latency_ms}


def _evidence_out(text_res: rules.TextRuleResult, items: list[EvidenceItem], llm: dict | None,
                  llm_level: str | None, notes: list[str]) -> list[dict]:
    pts = {id(it): p for it, p in scoring.evidence_points(items)}
    out = [{"source": it.source, "finding": it.finding, "weight": pts.get(id(it), 0)} for it in items]
    for s in text_res.signals:
        out.append({"source": "rules", "finding": s.reason, "weight": s.points})
    for n in notes:
        out.append({"source": "rules", "finding": n, "weight": 0})
    if llm is not None:
        out.append({"source": "llm", "finding": f"AI đánh giá mức nguy cơ: {llm_level}.",
                    "weight": scoring.LLM_SCORE.get(llm_level, 0)})
    return out[:20]


async def run(text: str | None, image: bytes | None, mime: str | None,
              providers: list[LLMProvider] | None = None, budget_s: float | None = None) -> dict:
    clock = _Clock(budget_s if budget_s is not None else total_timeout_s())
    providers = providers or []
    user_text = nfc(text or "").strip()
    notes: list[str] = []

    # 1. read
    image_text = None
    if image:
        image_text = await _ocr(image, mime or "image/png", providers, clock)
        if image_text is None:
            notes.append("Chưa đọc được chữ trong ảnh (chế độ hạn chế, chưa có AI đọc ảnh).")
        elif image_text == NO_TEXT_MARK:
            image_text = ""
            notes.append("Ảnh không có chữ.")
    source = "\n".join(t for t in (user_text, image_text or "") if t)  # quote check source

    # 2-3. entities + mask
    masker = Masker()
    masked = masker.mask(source)
    urls = extract_urls(source)

    # 4. evidence (parallel)
    items = await gather_evidence(urls, timeout_s=min(2.0, max(0.2, clock.remaining())))
    offstore = any(not u.official and not u.app_store for u in urls)
    text_res = rules.evaluate_text(source, has_offstore_url=offstore)
    rscore = scoring.rule_score(text_res, items)

    # 5. LLM (masked text only)
    llm, llm_model = (None, None)
    if source:
        ev_prompt = [it.for_prompt() for it in items] + [
            {"source": "rules", "signal": s.id, "finding": s.reason, "points": s.points} for s in text_res.signals]
        llm, llm_model = await _reason(masked, ev_prompt, providers, clock)
    llm_level = llm["risk_level"] if llm else None

    # 6. blend + post-checks
    final_score, level = scoring.blend(rscore, llm_level)
    mapping = masker.mapping

    llm_flags = []
    if llm:
        for f in llm.get("red_flags", []):
            q = postcheck.verify_quote(f.get("quote", ""), source, mapping)
            if q is None:
                continue  # hallucinated / non-verbatim quote -> dropped
            llm_flags.append({"quote": q, "reason": postcheck.humanize_tokens(f.get("reason", ""), mapping),
                              "tactic": f.get("tactic", "other")})
        dropped = len(llm.get("red_flags", [])) - len(llm_flags)
        if dropped:
            log.info("dropped non-verbatim quotes", extra={"n": dropped})

    rule_scn = text_res.scenario_id
    if not rule_scn and any(it.signal in ("domain_high", "domain_medium", "community_blacklist") for it in items):
        rule_scn = "G5.1"
    if not rule_scn and level != "low" and text_res.signals:
        rule_scn = text_res.topic_id
    if llm and llm.get("scenario_group") and level != "low":
        group, scenario_id = llm["scenario_group"], llm.get("scenario_id")
    elif level != "low" and rule_scn:
        group, scenario_id = rule_scn[:2], rule_scn if "." in rule_scn else None
    else:
        group, scenario_id = None, None

    agree = llm is not None and llm_level == level
    if agree and (level != "low" or "chưa thấy dấu hiệu lừa đảo" in llm["summary"].lower()):
        summary = postcheck.no_absolute_safety(postcheck.humanize_tokens(llm["summary"], mapping))
    else:
        reason = None
        if image and image_text is None and not user_text:
            reason = ("Chưa đọc được chữ trong ảnh. Hãy dán nội dung tin nhắn vào ô chữ để kiểm tra lại. "
                      "Đừng chuyển tiền khi chưa gọi lại số tổng đài chính thức.")
        summary = _summary(level, group, reason)

    if agree and llm.get("verification_questions"):
        questions = [postcheck.humanize_tokens(q, mapping) for q in llm["verification_questions"]]
    else:
        questions = QUESTIONS.get(scenario_id) or QUESTIONS.get(group) or QUESTIONS[None]
    if level == "low":
        action = "no_action"
    elif agree and llm.get("recommended_action") not in (None, "no_action"):
        action = llm["recommended_action"]
    else:
        action = "stop_and_verify"

    result = _build(
        level=level, score=final_score, group=group, scenario_id=scenario_id, summary=summary,
        flags=_merge_flags(llm_flags, text_res.signals, level), questions=questions, action=action,
        entities=_entities(masker, urls, source), evidence=_evidence_out(text_res, items, llm, llm_level, notes),
        model=llm_model or f"rules-only/{rules.RULES_VERSION}",
        prompt_version=llm["prompt_version"] if llm else "none",
        latency_ms=clock.elapsed_ms())

    errs = schema.errors(result)
    if errs:  # bug guard: never return an invalid result
        log.error("final result failed schema validation", extra={"n_errors": len(errs)})
        result = fallback_result(clock.elapsed_ms())
    log.info("analyze done", extra={
        "input_type": "image" if image else "text", "masked_len": len(masked), "n_urls": len(urls),
        "signals": [s.id for s in text_res.signals], "evidence": [it.signal for it in items],
        "rule_score": rscore, "llm_level": llm_level, "risk_level": result["risk_level"],
        "model": result["model"], "latency_ms": result["latency_ms"]})
    return result


def fallback_result(latency_ms: int = 0) -> dict:
    return _build(level="uncertain", score=30, group=None, scenario_id=None,
                  summary=_summary("uncertain", None), flags=[], questions=QUESTIONS[None],
                  action="stop_and_verify", entities=[],
                  evidence=[{"source": "rules", "finding": "Hệ thống đang ở chế độ hạn chế.", "weight": 0}],
                  model=f"rules-only/{rules.RULES_VERSION}", prompt_version="none", latency_ms=latency_ms)
