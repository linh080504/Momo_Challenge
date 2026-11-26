import time

from ...privacy.entities import extract
from ..contract import DISCLAIMER, LABELS, VALIDATOR
from ..pipeline.rules import BENIGN, match_rules
from ..providers.llm import PROMPT_VERSION, RISK, infer
from ..providers.ocr import read_image

QUESTIONS = [
    "Bạn đã gọi lại qua số lấy từ ứng dụng hoặc trang chính thức chưa?",
    "Người nhận tiền có đúng với người hoặc tổ chức bạn đã xác minh không?",
]


class Analyzer:
    def __init__(self, settings, store, signer, limits, safe_browsing):
        self.settings = settings
        self.store = store
        self.signer = signer
        self.limits = limits
        self.safe_browsing = safe_browsing

    def events(self, request, image):
        start = time.perf_counter()
        text = request.text.strip()
        if image is not None:
            text = "\n".join(filter(None, [text, read_image(image, self.settings)]))
            yield {"stage": "image_read", "message": "Đã đọc chữ trong ảnh"}
        keys, entities, domains = extract(text, request.url, self.signer)
        yield {"stage": "entities", "message": f"Đã trích {len(entities)} thông tin cần kiểm tra", "entities": entities}
        yield {"stage": "evidence", "message": "Đang tra bằng chứng"}

        evidence = []

        def add(source, finding, weight):
            evidence.append({"source": source, "finding": finding, "weight": weight})

        if self.store.matches(keys):
            add("internal_blacklist", "Trùng thông tin trong một chiến dịch đã được chuyên viên duyệt.", 60)
        worst_domain = max(({"low": 0, "medium": 20, "high": 45}[value["level"]]
                            for value in domains.values()), default=0)
        if worst_domain:
            add("domain_check", "Tên miền có tín hiệu bất thường. Hãy mở kênh chính thức để xác minh.", worst_domain)
        checked, found = self.safe_browsing.lookup(domains)
        if found:
            add("safe_browsing", "Google Safe Browsing ghi nhận tín hiệu nguy hiểm ở tên miền.", 60)
        elif checked:
            add("safe_browsing", "Không có kết quả trùng ở cấp tên miền.", 0)

        matches = match_rules(text)
        for rule, _ in matches:
            add("rules", rule.finding, rule.points)
        score = min(100, sum(item["weight"] for item in evidence))
        scenario = matches[0][0].scenario if matches else ("G5.1" if worst_domain or found else None)
        benign = bool(BENIGN.search(text))
        llm = infer(matches, evidence, benign, self.settings, self.limits)
        model = "rules"
        llm_level = None
        if llm:
            model, llm_level, prediction = llm
            score = max(score, RISK[llm_level])
            if llm_level != "low" and RISK[llm_level] >= 35:
                scenario = prediction or scenario
            add("llm", "Mô hình đã đánh giá các tín hiệu được trích xuất.", 0)
        level = (
            "high" if score >= 60 else "medium" if score >= 35 else
            "low" if (score <= 15 and llm_level == "low") or (score == 0 and benign) else "uncertain"
        )
        output = {
            "risk_level": level, "risk_score": score, "scenario_group": scenario.split(".")[0] if scenario else None,
            "scenario_id": scenario, "summary": LABELS[level],
            "red_flags": [{"quote": quote, "reason": rule.finding, "tactic": rule.tactic}
                          for rule, quote in matches[:3]],
            "verification_questions": QUESTIONS,
            "recommended_action": "no_action" if level == "low" else "stop_and_verify",
            "evidence": evidence, "entities": entities, "ai_disclaimer": DISCLAIMER,
            "model": model, "prompt_version": PROMPT_VERSION,
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "degraded": llm is None or bool(domains and not checked),
        }
        VALIDATOR.validate(output)
        yield {"result": output, "keys": keys}
