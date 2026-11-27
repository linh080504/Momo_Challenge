import asyncio
import gzip
import json

import httpx
import pytest

from app.analyzer.providers import llm
from app.auth.security import Limits
from app.config import Settings
from app.evidence import public_page
from app.evidence.website_explanation import public_explanation_options


class Body(httpx.AsyncByteStream):
    def __init__(self, data):
        self.data = data

    async def __aiter__(self):
        yield self.data


@pytest.mark.parametrize(("ip", "redirect", "status", "request_count"), [
    ("8.8.8.8", None, "read", 2),
    ("8.8.8.8", "https://example.org/", "redirect", 2),
    ("127.0.0.1", None, "restricted", 1),
])
def test_reads_pinned_public_address_only(monkeypatch, ip, redirect, status, request_count):
    requests = []

    def handle(request):
        requests.append(request.url)
        if len(requests) == 1:
            assert request.url.host == "cloudflare-dns.com"
            assert request.url.params["name"] == "example.com"
            return httpx.Response(200, json={"Answer": [{"type": 1, "data": ip}]})
        assert request.url.host == ip and request.headers["host"] == "example.com"
        assert request.headers["user-agent"] == "PayPause/0.1"
        assert request.url.query == b"" and request.extensions["sni_hostname"] == "example.com"
        if redirect:
            return httpx.Response(302, headers={"location": redirect})
        return httpx.Response(200, stream=Body(gzip.compress(b"<h1>Example</h1>")),
                              headers={"content-type": "text/html", "content-encoding": "gzip"})

    client_class = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client_class(transport=httpx.MockTransport(handle), **kwargs))
    found, _, _ = asyncio.run(public_page._fetch("https://example.com/read?token=private"))
    assert found == status and len(requests) == request_count


def test_gzip_body_rejects_oversized_decoded_html():
    response = httpx.Response(200, stream=Body(gzip.compress(b"x" * 64_000)), headers={"content-encoding": "gzip"})
    assert asyncio.run(public_page._read_body(response, 1024)) == ("too_large", None)


def test_recording_loads_publisher_styles_and_fonts_through_public_gateway(monkeypatch):
    url = "https://humanactprize.org/read"
    stylesheet = "https://static.mediacdn.vn/HAP/style.css"
    font = "https://static.mediacdn.vn/HAP/fonts/body.woff2"
    html = (f'<link rel="stylesheet" href="{stylesheet}?v=3">'
            '<link rel="stylesheet" href="https://example.org/unrelated.css">')
    fetched = []

    async def resolve(_client, host):
        assert host == "static.mediacdn.vn"
        return "8.8.8.8"

    def respond(request):
        assert request.url.host == "8.8.8.8"
        assert request.url.query == b""
        fetched.append(request.url.path)
        if request.url.path == "/HAP/style.css":
            css = b'@font-face{font-family:Body;src:url(fonts/body.woff2)}' + b" " * 550_000
            return httpx.Response(200, stream=Body(gzip.compress(css)),
                                  headers={"content-type": "text/css", "content-encoding": "gzip"})
        return httpx.Response(200, stream=Body(b"wOF2data"), headers={"content-type": "application/font-woff2"})

    client_class = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client_class(transport=httpx.MockTransport(respond), **kwargs))
    monkeypatch.setattr(public_page, "_resolve", resolve)
    assets = asyncio.run(public_page._read_assets(html, url))

    assert fetched == ["/HAP/style.css", "/HAP/fonts/body.woff2"]
    assert assets[f"{stylesheet}?v=3"][:2] == ("stylesheet", "text/css")
    assert assets[font] == ("font", "font/woff2", b"wOF2data")


def test_qwen_explains_classified_signals_without_republishing_promotion(monkeypatch):
    html = """<h1>Casino XYZ</h1><p>Nạp tiền để tham gia cá cược và nhận thưởng nạp.</p>
    <p>Đây là trang chính thức đã được cấp phép. Xem hướng dẫn nạp/rút tiền.</p>
    <script>document.write('chuyển ngay để nhận thưởng')</script>"""
    facts, findings, title = public_page.parse_public_page(html, "https://offers.example.com")
    assert facts["gambling_offer"] and not facts["payment_pressure"]
    assert title is None and "XYZ" not in " ".join(findings)
    domain = {"host": "offers.example.com", "registered_domain": "example.com", "score": 0, "official_brand": None}
    options = public_explanation_options(facts, domain, sources_checked=False)

    def reply(_instructions, payload_json, _key, _timeout, _max_output_tokens):
        assert "XYZ" not in payload_json and "public_excerpts" not in payload_json
        return json.dumps({"risk_level": "medium", "scenario_id": None,
                           "reason_ids": ["operator_claim", "withdrawal", "unverified_license", "subdomain"]})

    monkeypatch.setattr(llm, "_qwen_output", reply)
    _, _, _, explanation = llm.infer([], [], False, Settings(dashscope_api_key="test", llm_calls_per_day=1),
                                     Limits(), website_context={"public_html": facts}, explanation_options=options)

    assert explanation[:4] == [options[key] for key in ("gambling_offer", "payment_incentive", "operator_claim", "withdrawal")]
    assert explanation[4] == options["subdomain"]
    assert "HTML" not in str(explanation)


def test_news_homepage_extracts_article_teasers_without_heading():
    teaser = "The local paper published an article about libraries extending their opening hours."
    other = "The paper also published an article about the team organizing a neighborhood cleanup."
    html = (f"<title>Local paper</title><script>let html = '<article><p>{teaser}</p></article>';</script>"
            f"<article><p>{teaser}</p></article><article><p>{other}</p></article>"
            "<p>Subscribe to receive updates about all our stories and other notices from the company.</p>")
    facts, _, title = public_page.parse_public_page(html, "https://example.org/")
    assert title == "Local paper"
    assert facts["homepage"] is True
    assert facts["article_count"] == 2
    assert facts["public_excerpts"] == [teaser, other]


@pytest.mark.parametrize("fenced", [False, True])
def test_qwen_public_explanation_is_selected_from_verified_facts(monkeypatch, fenced):
    html = ('<meta name="description" content="Community project https://example.com/private-marker">'
            '<article><h1>Test article</h1><p>Our community project provides information and training to the '
            'public. See https://example.com/private-article-marker for more.</p>'
            '<p>The project also brings together several reading groups and offers a library of materials.</p></article>')
    facts, _, title = public_page.parse_public_page(html, "https://example.com")
    facts["public_title"] = title
    options = public_explanation_options(facts, {"score": 0, "official_brand": None}, sources_checked=False)

    def reply(instructions, payload_json, _key, timeout, max_output_tokens):
        assert timeout == 12.0 and max_output_tokens >= 500
        assert "reason_ids" in instructions
        payload = json.loads(payload_json)
        assert set(payload["explanation_options"]) == set(options)
        assert payload["website_context"]["public_html"]["public_title"] == "Test article"
        assert "private-marker" not in payload_json
        assert "private-article-marker" not in payload_json
        output = json.dumps({"risk_level": "uncertain", "scenario_id": None,
                             "page_purpose": "project_profile",
                             "content_analysis": [
                                 {"excerpt_index": 0, "text": "Bài giới thiệu một dự án cung cấp thông tin và đào tạo cho cộng đồng."},
                                 {"excerpt_index": 1, "text": "Bài cho biết tên miền này đã được đăng ký vào năm 2020."},
                             ],
                             "reason_ids": ["article_structure", "unverified_license", "scope", "scope"]})
        return f"```json\n{output}\n```" if fenced else output

    monkeypatch.setattr(llm, "_qwen_output", reply)
    result = llm.infer([], [], False, Settings(dashscope_api_key="test", llm_calls_per_day=1), Limits(),
                       website_context={"public_html": facts}, explanation_options=options)
    model, risk, scenario, explanation = result
    assert (model, risk, scenario) == ("qwen4-max", "uncertain", None)
    assert explanation[0]["label"] == "Nội dung bài"
    assert "đào tạo cho cộng đồng" in explanation[0]["finding"]
    assert "Our community project" in explanation[0]["support"]
    assert "2020" not in str(explanation)
    assert explanation[1:3] == [options["article_structure"], options["scope"]]
    assert explanation[-1] == options["source_gap"]
