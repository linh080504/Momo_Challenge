import time

from ...evidence.rdap import lookup_age
from ...evidence.url_gateway import checked_destination
from ...privacy.entities import extract
from ...qr.checks import evaluate_payment
from ..contract import DISCLAIMER, LABELS, VALIDATOR
from ..evidence.blacklist import lookup as community_domain_match
from ..signals.document import inspect_document
from ..signals.knowledge import retrieve_guidance
from ..signals.rules import BENIGN, match_rules
from ..providers.fraud_url import FraudURL
from ..providers.llm import PROMPT_VERSION, RISK, infer
from ..providers.ocr import read_document, read_image
from ..providers.speech import read_speech

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
        self.fraud_url = FraudURL(settings.fraud_url_model_path) if settings.fraud_url_model_path else None

    def events(self, request, image):
        start = time.perf_counter()
        text = request.text.strip()
        inputs = ["text"] if text else []
        document = None
        if image is not None:
            inputs.append(request.image_kind)
            if request.image_kind == "receipt":
                recognized, boxes = read_document(image, self.settings)
                document = inspect_document(image, request.image_mime, recognized, boxes)
            else:
                recognized = read_image(image, self.settings)
            text = "\n".join(filter(None, [text, recognized]))
            yield {"stage": "image_read", "message": "Đã đọc chữ trong ảnh"}
        if request.audio_base64:
            inputs.append("audio")
            text = "\n".join(filter(None, [text, read_speech(request.audio_base64, self.settings)]))
            yield {"stage": "audio_read", "message": "Đã nhận dạng lời nói"}
        qr = None
        supplement = text
        if request.qr_payload:
            inputs.append("qr")
            if request.qr_payload.lower().startswith(("https://", "http://")):
                supplement += "\n" + request.qr_payload
            else:
                qr, payment = evaluate_payment(request.qr_payload, text, self.store, self.signer)
            yield {"stage": "qr_read", "message": "Đã đọc nội dung mã QR"}
        keys, entities, domains = extract(supplement, request.url, self.signer)
        if domains:
            inputs.append("url")
        if qr and qr.valid_crc and len(keys) < 30:
            digest = self.signer.digest("ACCOUNT", qr.account)
            if digest not in keys:
                keys[digest] = "ACCOUNT"
                entities.append({"type": "ACCOUNT", "display": payment["account"]})
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
        if any(item["lookup_allowed"] and community_domain_match(host) for host, item in domains.items()):
            add("external_blacklist", "Tên miền xuất hiện trong danh sách cảnh báo cộng đồng vn-badsite-filter.", 45)
        url_score = self.fraud_url.score(domains) if self.fraud_url else None
        if url_score is not None and url_score >= .85 and worst_domain:
            add("fraud_url_ml", "Mô hình URL ghi nhận thêm tín hiệu tương đồng với mẫu phishing đã gán nhãn.", 15)
        if qr:
            add("vietqr", "Đã đọc cấu trúc VietQR. Hãy đối chiếu người nhận và số tiền.", 0)
            if not qr.valid_crc or payment["mismatch"]:
                add("vietqr", "Mã kiểm tra hoặc tài khoản trong QR không khớp.", 40)
        checked, found = self.safe_browsing.lookup(domains)
        if found:
            add("safe_browsing", "Google Safe Browsing ghi nhận tín hiệu nguy hiểm ở tên miền.", 60)
        elif checked:
            add("safe_browsing", "Không có kết quả trùng ở cấp tên miền.", 0)
        if age := lookup_age(domains, self.limits, self.settings.rdap_lookups_per_hour):
            host, days = age
            domains[host]["domain_age_days"] = days
            add("rdap", "RDAP ghi nhận tên miền mới đăng ký trong 30 ngày." if days < 30
                else "Đã đối chiếu thời điểm đăng ký với cơ sở dữ liệu tên miền.", 15 if days < 30 else 0)

        matches = match_rules(text)
        for rule, _ in matches:
            add("rules", rule.finding, rule.points)
        if document:
            add("document", "Đã phân tích ảnh biên lai. Cần đối chiếu giao dịch với ngân hàng.", 0)
        score = min(100, sum(item["weight"] for item in evidence))
        scenario = matches[0][0].scenario if matches else ("G5.1" if worst_domain or found else None)
        benign = bool(BENIGN.search(text))
        fast = (found and not matches) or any(item["source"] == "internal_blacklist" for item in evidence) or (
            benign and not matches and not entities and inputs == ["text"]
        )
        guidance = retrieve_guidance(matches, bool(worst_domain or found))
        llm = None if fast else infer(matches, evidence, benign, self.settings, self.limits, guidance)
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
            "analysis_path": "fast" if fast else "deep",
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "degraded": (not fast and llm is None) or bool(domains and not checked and not found),
        }
        if document is not None:
            output["document"] = document
        if domains:
            output["url_checks"] = [checked_destination(item) for item in domains.values()]
        if url_score is not None:
            output["specialized_models"] = {"fraud_url": self.fraud_url.version}
        if guidance:
            output["guidance"] = guidance
        VALIDATOR.validate(output)
        yield {"result": output, "keys": keys, "inputs": inputs}
