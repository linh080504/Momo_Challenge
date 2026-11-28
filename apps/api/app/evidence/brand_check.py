import re

import idna
from rapidfuzz.distance import Levenshtein

from .url_gateway import BRAND_CONFUSABLES, inspect_url

VERSION = "momo-brand-v1"
OFFICIAL_HOSTS = {"momo.vn", "www.momo.vn", "payment.momo.vn"}
SHARED_HOSTS = {"docs.google.com", "sites.google.com", "forms.gle", "drive.google.com", "notion.so",
                "www.notion.so", "facebook.com", "www.facebook.com", "t.me"}
DEMO_HOST = "momo-hoan-tien.example"
APPROVED_FINDING = "Chuyên viên PayPause đã xác nhận website mạo danh MoMo."
BRAND = re.compile(r"(?<!\w)momo(?!\w)", re.IGNORECASE)
BRAND_ACTION = re.compile(r"\b(?:xác minh|xác thực|đăng nhập|hoàn tiền|hỗ trợ|verify|sign in)\b", re.IGNORECASE)
FINDINGS = {
    "verified_host": "Tên miền nằm trong danh mục MoMo hoặc đối tác đã xác minh.",
    "similar_host": "Tên miền có dấu hiệu tương tự địa chỉ MoMo.",
    "brand_heading": "Tiêu đề trang dùng tên MoMo và yêu cầu thao tác liên quan đến tài khoản hoặc hoàn tiền.",
    "visual_brand": "Tên MoMo xuất hiện trong chữ đọc được từ ảnh giao diện.",
    "sensitive_form": "Trang có trường nhập mật khẩu, mã xác thực hoặc dữ liệu thẻ.",
    "external_form": "Biểu mẫu được cấu hình gửi dữ liệu sang một tên miền khác.",
    "account_request": "Trang đề nghị nhập hoặc gửi thông tin nhạy cảm.",
    "education": "Tiêu đề cho thấy đây có thể là nội dung hướng dẫn phòng tránh.",
    "shared_host": "Nền tảng dùng chung hoặc rút gọn cần được xem xét theo từng địa chỉ cụ thể.",
    "missing_content": "Chưa đọc được nội dung trang để đối chiếu thương hiệu và biểu mẫu.",
    "incomplete_content": "Chưa xác định đủ ngữ cảnh hoặc đích gửi thông tin để kết luận mạo danh.",
}


def candidate_domain(value):
    domain = inspect_url(value)
    if not domain["lookup_allowed"] and domain["host"] != DEMO_HOST:
        raise ValueError("unsupported domain")
    return domain


def brand_claim(heading):
    return bool(BRAND.search(heading) and BRAND_ACTION.search(heading))


def looks_like_momo(domain):
    base = domain["registered_domain"]
    if not base:
        return False
    label = idna.decode(base).split(".")[0].casefold().translate(BRAND_CONFUSABLES).replace("-", "")
    return "momo" in label or Levenshtein.distance(label, "momo") <= 1


def verified_hosts(settings):
    return OFFICIAL_HOSTS | {host.strip().lower().rstrip(".") for host in settings.momo_partner_hosts.split(",") if host.strip()}


def evaluate_brand(domain, facts=None, screenshot_text=None, *, partner=False):
    host = domain["host"]
    verified = host in OFFICIAL_HOSTS or partner
    similar = looks_like_momo(domain)
    claim = bool((facts or {}).get("momo_heading_claim"))
    visual = bool(screenshot_text and BRAND.search(screenshot_text))
    education = bool((facts or {}).get("educational_heading"))
    sensitive = bool((facts or {}).get("sensitive_inside_form"))
    external = bool((facts or {}).get("sensitive_external_form"))
    request = sensitive and bool((facts or {}).get("account_request"))
    shared = host in SHARED_HOSTS or any(signal["signal"] == "shortener" for signal in domain["signals"])
    codes = [code for code, present in (
        ("verified_host", verified), ("similar_host", similar and not verified),
        ("brand_heading", claim), ("visual_brand", visual),
        ("sensitive_form", sensitive), ("external_form", external),
        ("account_request", request), ("education", education), ("shared_host", shared),
    ) if present]
    if not facts:
        verdict = "ABSTAIN_NEEDS_REVIEW"
        codes.append("missing_content")
    elif shared or (facts or {}).get("meta_redirect"):
        verdict = "ABSTAIN_NEEDS_REVIEW"
        codes.append("incomplete_content")
    elif not verified and claim and sensitive and (external or request) and not education:
        verdict = "IMPOSTOR"
    elif (verified and not (external and sensitive)) or (not sensitive and (education or not (similar or claim or visual))):
        verdict = "BENIGN"
    else:
        verdict = "ABSTAIN_NEEDS_REVIEW"
        codes.append("incomplete_content")
    return {"verdict": verdict, "version": VERSION, "evidence": codes}


def describe_brand(assessment):
    return {**assessment, "findings": [FINDINGS[code] for code in assessment["evidence"]]}
