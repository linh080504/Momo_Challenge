import time

from ...evidence.public_article import PUBLIC_ARTICLES, read_public_article
from ...evidence.public_page import read_public_page
from ...evidence.rdap import lookup_age
from ...evidence.url_gateway import checked_destination
from ...evidence.website_report import build_report, credential_labels, markup_signals, screenshot_brands
from ...evidence.website_explanation import public_explanation_options
from ...privacy.entities import URL, extract
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
        screenshot_text = None
        if image is not None:
            inputs.append(request.image_kind)
            if request.image_kind == "receipt":
                recognized, boxes = read_document(image, self.settings)
                document = inspect_document(image, request.image_mime, recognized, boxes)
            else:
                recognized = read_image(image, self.settings)
                screenshot_text = recognized
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
        explicit_website = bool(request.website_preview and request.url)
        if age := lookup_age(domains, self.limits, self.settings.rdap_lookups_per_hour, explicit_website=explicit_website):
            host, days, registered = age
            domains[host]["domain_age_days"] = days
            domains[host]["domain_registered_on"] = registered
            add("rdap", "RDAP ghi nhận tên miền mới đăng ký trong 30 ngày." if days < 30
                else "Đã đối chiếu thời điểm đăng ký với cơ sở dữ liệu tên miền.", 15 if days < 30 else 0)

        matches = match_rules(text)
        for rule, _ in matches:
            add("rules", rule.finding, rule.points)
        if document:
            add("document", "Đã phân tích ảnh biên lai. Cần đối chiếu giao dịch với ngân hàng.", 0)
        markup = markup_signals(request.website_html, request.url) if request.website_html and request.url else None
        markup_needs_review = markup is not None and (markup["status"] == "unreadable" or bool(markup["findings"]))
        website_context = None
        if request.website_preview and request.url and domains and (screenshot_text is not None or markup is not None):
            host = next(iter(domains))
            website_context = {
                "has_screenshot": screenshot_text is not None,
                "credential_labels": credential_labels(screenshot_text or ""),
                "brand_mentions_off_domain": sum(not item["domain_matches"] for item in screenshot_brands(screenshot_text or "", host)),
                "html_findings": markup["findings"] if markup else [],
            }
        score = min(100, sum(item["weight"] for item in evidence))
        article = None
        public_page = None
        explanation_options = None
        if explicit_website and inputs == ["url"] and markup is None:
            target = request.url.strip()
            if target in PUBLIC_ARTICLES and score == 0:
                article = read_public_article(target, self.settings, self.limits)
                if article:
                    yield {"stage": "website_read", "message": "Đã đọc đề mục và cấu trúc bài viết"}
            elif self.settings.website_public_html_enabled:
                message = ("Đang mở website và chụp ảnh" if self.settings.website_capture_enabled
                           else "Đang đọc nội dung công khai của trang")
                yield {"stage": "website_read", "message": message}
                public_page, public_facts = read_public_page(target, capture=self.settings.website_capture_enabled)
                if public_facts:
                    website_context = {"public_html": public_facts}
                    explanation_options = public_explanation_options(public_facts, next(iter(domains.values())),
                                                                    checked or found, evidence)
                    if public_facts["sensitive_form"] and public_facts["external_form"]:
                        add("website_content", "Trang khai báo trường nhạy cảm và gửi biểu mẫu sang tên miền khác.", 35)
                    if public_facts["gambling_offer"]:
                        add("website_content", "Trang có dấu hiệu mời cá cược kèm nạp tiền. Tránh gửi tiền hoặc thông tin cá nhân.", 35)
                    score = min(100, sum(item["weight"] for item in evidence))
        educational_article = article is not None and article["context"] == "educational"
        scenario = matches[0][0].scenario if matches else ("G5.1" if worst_domain or found else None)
        benign = bool(BENIGN.search(text))
        familiar_message = benign and not entities and set(inputs) <= {"text", "image"}
        single_link_input = (inputs == ["url"] or
                             (inputs == ["text", "url"] and request.url is None and URL.fullmatch(text)) or
                             (inputs == ["qr", "url"] and request.url is None and qr is None))
        official_link = single_link_input and len(domains) == 1 and next(iter(domains.values()))["official_homepage"]
        valid_vietqr = inputs == ["qr"] and qr is not None and payment["risk"] == "low"
        low_from_checks = score == 0 and not markup_needs_review and (
            familiar_message or official_link or valid_vietqr or educational_article
        )
        confirmed = any(item["source"] == "internal_blacklist" for item in evidence)
        needs_model = website_context is not None or (not low_from_checks and not confirmed and not (found and not matches) and score > 0)
        if low_from_checks and official_link:
            add("domain_check", "Địa chỉ trang chủ HTTPS khớp danh sách tên miền chính thức.", 0)
        if explanation_options:
            stage = {"stage": "website_ai", "message": "Qwen4-Max đang đánh giá bằng chứng từ website"}
            if picture := public_page.get("capture_jpeg"):
                stage["website_capture"] = {"jpeg": picture, "host": next(iter(domains))}
            yield stage
        guidance = retrieve_guidance(matches, bool(worst_domain or found), text)
        llm = infer(matches, evidence, benign, self.settings, self.limits, guidance, website_context,
                    explanation_options) if needs_model else None
        model = article["model"] if article and article["model"] else "rules"
        llm_level = None
        if llm:
            model, llm_level, prediction, explanation = llm
            model_score = RISK[llm_level]
            if public_page and score <= 35:
                model_score = min(model_score, max(score, RISK["uncertain"]))
            elif website_context is not None and score == 0:
                # Unverified visual context can request further review. Existing evidence controls warning levels.
                model_score = min(model_score, RISK["uncertain"])
            score = max(score, model_score)
            if llm_level != "low" and model_score >= 35:
                scenario = prediction or scenario
            add("llm", "Mô hình đã đánh giá các tín hiệu được trích xuất.", 0)
            if explanation and public_page:
                public_page["explanation"] = explanation
        if public_page and public_page["status"] == "read":
            public_page["model"] = model if llm else None
            public_page["checked_at"] = int(time.time())
        level = (
            "high" if score >= 60 else "medium" if score >= 35 else
            "low" if low_from_checks or (score <= 15 and llm_level == "low" and document is None
                                         and not markup_needs_review and website_context is None) else "uncertain"
        )
        output = {
            "risk_level": level, "risk_score": score, "scenario_group": scenario.split(".")[0] if scenario else None,
            "scenario_id": scenario, "summary": ("Đã đọc bài viết từ nguồn chính thức. Các đề mục tập trung vào hướng dẫn "
                                                  "phòng tránh lừa đảo." if educational_article else LABELS[level]),
            "red_flags": [{"quote": quote, "reason": rule.finding, "tactic": rule.tactic}
                          for rule, quote in matches[:3]],
            "verification_questions": QUESTIONS,
            "recommended_action": "no_action" if level == "low" else "stop_and_verify",
            "evidence": evidence, "entities": entities, "ai_disclaimer": DISCLAIMER,
            "model": model, "prompt_version": PROMPT_VERSION,
            "analysis_path": "deep" if needs_model or article and article["model"] else "fast",
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "degraded": (needs_model and llm is None) or bool(domains and not checked and not found),
        }
        if document is not None:
            output["document"] = document
        if domains:
            output["url_checks"] = [checked_destination(item) for item in domains.values()]
            output["website_report"] = build_report(domains, evidence, screenshot_text, checked, found, markup, self.settings)
            if article:
                output["website_report"]["article"] = article
            if explicit_website:
                output["website_report"]["capture_scope"] = "listed" if request.url.strip() in PUBLIC_ARTICLES else "unlisted"
            if public_page:
                output["website_report"]["public_page"] = public_page
        if url_score is not None:
            output["specialized_models"] = {"fraud_url": self.fraud_url.version}
        if guidance:
            output["guidance"] = guidance
        VALIDATOR.validate(output)
        yield {"result": output, "keys": keys, "inputs": inputs}
