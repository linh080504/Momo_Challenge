import base64
import io
import json
import os
import wave
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont
from pydantic import SecretStr

from app.analyzer.contract import VALIDATOR
from app.config import Settings
from app.evidence.url_gateway import inspect_url
from app.kit import vietqr
from app.main import create_app

ACCOUNT = "0000012345"
TEXT = f"Tài khoản tạm giữ. Chuyển ngay qua STK {ACCOUNT}, tuyệt đối không được nói với ai."
DEMO_PASSWORD = "for-automated-tests-only"


@pytest.fixture
def configured(tmp_path):
    return Settings(
        _env_file=None, database_url=f"sqlite:///{(tmp_path / 'test.sqlite3').as_posix()}",
        app_secret="automated-test-secret-value-over-32-chars",
        demo_user_email="user@example.invalid", demo_user_password=DEMO_PASSWORD,
        demo_ops_email="ops@example.invalid", demo_ops_password=DEMO_PASSWORD,
        dashscope_api_key="", safe_browsing_key="",
        fraud_url_model_path="", rdap_lookups_per_hour=0, whisper_command="", whisper_model_path="",
    )


@pytest.fixture
def client(configured):
    with TestClient(create_app(configured)) as test_client:
        yield test_client


def login(client, role):
    response = client.post("/v1/auth/login", json={"email": role + "@example.invalid", "password": DEMO_PASSWORD})
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["token"]}


def analyze(client, text=TEXT, headers=None):
    response = client.post("/v1/analyze", json={"text": text}, headers=headers)
    assert response.status_code == 200, response.text
    result = response.json()
    VALIDATOR.validate(result)
    return result


def report(client, headers, result):
    response = client.post("/v1/reports", json={"analysis_id": result["analysis_id"], "consent": True}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["campaign_id"]


def image_body(image):
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return {"image_base64": base64.b64encode(buffer.getvalue()).decode(), "image_mime": "image/png"}


def test_schema_quotes_risk_and_privacy(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/ready").json()["status"] == "ready"
    result = analyze(client)
    assert result["risk_level"] == "high"
    assert result["degraded"] is True
    assert len(result["red_flags"]) == 3
    assert all(flag["quote"] in TEXT for flag in result["red_flags"])
    assert ACCOUNT not in json.dumps(result)
    assert analyze(client, "Mẹ ơi tối con về ăn cơm nhé")["risk_level"] == "low"
    assert analyze(client, "Vui lòng không cung cấp mã OTP cho ai")["risk_level"] == "low"
    assert analyze(client, "Xin trao đổi thêm")["risk_level"] == "uncertain"


def test_loan_approval_routes_to_qwen_as_context_without_raising_risk(configured, monkeypatch):
    from app.analyzer.providers import llm

    configured.dashscope_api_key = SecretStr("fake-qwen-key")
    calls = []

    def reply(_instructions, payload, *_):
        facts = json.loads(payload)
        assert facts["signals"] and "khoản vay" in facts["signals"][0]
        assert "private-message-marker" not in payload and "6.000.000" not in payload
        calls.append(facts)
        return '{"risk_level":"high","scenario_id":"G5.4"}'

    monkeypatch.setattr(llm, "_qwen_output", reply)
    message = "Yêu cầu vay 6.000.000 VND được phê duyệt sơ bộ. Hồ sơ private-message-marker."
    with TestClient(create_app(configured)) as client:
        result = analyze(client, message)

    assert len(calls) == 1
    assert (result["model"], result["analysis_path"], result["degraded"]) == ("qwen4-max", "deep", False)
    assert (result["risk_level"], result["risk_score"], result["scenario_id"]) == ("uncertain", 0, None)
    assert result["red_flags"] == []
    assert result["content_context"][0]["quote"] == "Yêu cầu vay"


@pytest.mark.parametrize(("statement", "risk"), [
    ("Vui lòng nộp phí giải ngân.", "medium"),
    ("Bạn không cần phải nộp phí giải ngân.", "uncertain"),
])
def test_loan_fee_signal_distinguishes_requests_from_negation(client, statement, risk):
    result = analyze(client, f"Hồ sơ vay đã được duyệt. {statement}")
    assert result["risk_level"] == risk
    assert any(flag["quote"] == "nộp phí giải ngân" for flag in result["red_flags"]) == (risk == "medium")


def test_job_message_and_payment_qr_distinguish_context_from_advance_fee(client):
    text = "Tin tuyển dụng cho ứng viên làm việc tại nhà."
    notice = analyze(client, text)
    assert notice["risk_level"] == "uncertain"
    assert not notice["red_flags"] and notice["content_context"]
    risky = text + " Ứng viên phải nạp tiền để thực hiện nhiệm vụ."
    assert analyze(client, risky)["scenario_id"] == "G3.1"
    payload = vietqr.build("970436", ACCOUNT, 50000)
    assert client.post("/v1/qr/parse", json={"payload": payload, "text": text}).json()["risk"] == "low"
    assert client.post("/v1/qr/parse", json={"payload": payload, "text": risky}).json()["risk"] == "medium"


@pytest.mark.parametrize(("payload", "status"), [
    ({}, 422),
    ({"image_base64": "!", "image_mime": "image/jpeg"}, 422),
    ({"image_base64": "R0lG", "image_mime": "image/gif"}, 415),
    ({"image_base64": "R0lG", "image_mime": "image/png"}, 422),
    ({"image_base64": "A" * (7 * 1024 * 1024), "image_mime": "image/jpeg"}, 413),
])
def test_invalid_inputs_are_errors(client, payload, status):
    response = client.post("/v1/analyze", json=payload)
    assert response.status_code == status
    assert "risk_level" not in response.json()


def test_stream_uses_ocr_output_and_real_progress(client, monkeypatch):
    from app.analyzer.agents import analyze as agent

    monkeypatch.setattr(agent, "read_image", lambda image, settings: TEXT)
    response = client.post("/v1/analyze/stream", json=image_body(Image.new("RGB", (50, 40), "white")))
    assert response.status_code == 200
    events = [json.loads(line) for line in response.text.splitlines()]
    assert [event["stage"] for event in events[:-1]] == ["image_read", "entities", "evidence"]
    assert events[-1]["result"]["risk_level"] == "high"
    assert ACCOUNT not in response.text


@pytest.mark.parametrize("vision_ok", [True, False])
def test_qwen_vision_requires_consent_and_uses_local_fallback(configured, monkeypatch, vision_ok):
    from app.analyzer.agents import analyze as agent
    from app.analyzer.providers import llm

    configured.dashscope_api_key = SecretStr("fake-qwen-key")
    calls = []
    monkeypatch.setattr(agent, "read_image", lambda *_: "Con về ăn cơm nhé.")

    def reply(instructions, data, _key, _timeout, _max_output_tokens):
        if isinstance(data, list):
            assert "chép lại NGUYÊN VĂN" in instructions
            assert data[0]["content"][0] == {
                "type": "input_text", "text": "Chép lại nguyên văn toàn bộ chữ trong ảnh đính kèm.",
            }
            image = data[0]["content"][1]
            assert image["type"] == "input_image" and image["image_url"].startswith("data:image/jpeg;base64,")
            calls.append(image)
            return "Gửi mã OTP để xác minh." if vision_ok else "[KHÔNG CÓ CHỮ]"
        assert "data:image" not in data
        assert json.loads(data)["screenshot_excerpts"] == ["Gửi mã OTP để xác minh."]
        return '{"risk_level":"high","scenario_id":"G5.4"}'

    monkeypatch.setattr(llm, "_qwen_output", reply)
    body = image_body(Image.new("RGB", (50, 40), "white"))
    with TestClient(create_app(configured)) as client:
        default = client.post("/v1/analyze", json=body).json()
        assert not calls and default["image_reader"] == "local_ocr"
        wrong_type = client.post("/v1/analyze", json={**body, "image_kind": "receipt", "qwen_vision": True})
        assert wrong_type.status_code == 422 and not calls
        vision = client.post("/v1/analyze", json={**body, "qwen_vision": True}).json()
    assert len(calls) == 1
    assert vision["image_reader"] == ("qwen4-max" if vision_ok else "local_ocr_fallback")
    assert vision["risk_level"] == ("high" if vision_ok else "low")


@pytest.mark.parametrize(("quote", "risk"), [
    ("Bạn cần ứng trước một khoản để nhận lại tiền", "medium"),
    ("Người gửi đòi mã xác thực", "uncertain"),
])
def test_vision_transcript_is_analyzed_with_grounded_flags(configured, monkeypatch, quote, risk):
    from app.analyzer.providers import llm

    configured.dashscope_api_key = SecretStr("fake-qwen-key")

    def reply(instructions, data, *_args):
        if isinstance(data, list):
            return "Bạn cần ứng trước một khoản để nhận lại tiền. Mã hồ sơ 465232. Email sample@example.invalid."
        assert "screenshot_flags" in instructions
        assert "465232" not in data and "sample@example.invalid" not in data
        return json.dumps({"risk_level": "high", "scenario_id": None, "screenshot_flags": [
            {"excerpt_index": 0, "quote": quote, "tactic": "personal_account"},
        ]})

    monkeypatch.setattr(llm, "_qwen_output", reply)
    with TestClient(create_app(configured)) as client:
        response = client.post("/v1/analyze", json={
            **image_body(Image.new("RGB", (50, 40), "white")), "qwen_vision": True,
        })
    assert response.status_code == 200
    result = response.json()
    assert (result["model"], result["analysis_path"], result["risk_level"]) == ("qwen4-max", "deep", risk)
    assert [flag["quote"] for flag in result["red_flags"]] == ([quote] if risk == "medium" else [])


def test_public_input_contract_and_qr_result_variants(client):
    paths = client.get("/openapi.json").json()["paths"]
    ask = paths["/v1/analyze"]["post"]
    stream = paths["/v1/analyze/stream"]["post"]
    parse = paths["/v1/qr/parse"]["post"]
    inputs = ask["requestBody"]["content"]["application/json"]["schema"]["properties"]
    assert set(inputs) == {"text", "image_base64", "image_mime", "image_kind", "qwen_vision", "audio_base64", "qr_payload", "url",
                           "website_html", "website_preview", "locale"}
    assert set(stream["responses"]["200"]["content"]) == {"application/x-ndjson"}
    variants = parse["responses"]["200"]["content"]["application/json"]["schema"]["discriminator"]
    assert variants["propertyName"] == "kind"
    assert set(variants["mapping"]) == {"url", "payment"}
    assert client.post("/v1/qr/parse", json={"payload": "invalid QR"}).status_code == 422


def test_stream_ends_with_one_error_if_later_input_fails(client, monkeypatch):
    from app.analyzer.agents import analyze as agent

    monkeypatch.setattr(agent, "read_image", lambda image, settings: TEXT)
    data = {**image_body(Image.new("RGB", (50, 40), "white")), "qr_payload": "invalid QR"}
    response = client.post("/v1/analyze/stream", json=data)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    first, last = [json.loads(line) for line in response.text.splitlines()]
    assert first["stage"] == "image_read"
    assert last["status"] == 422 and last["error"] and "result" not in last
    assert client.post("/v1/analyze", json=data).status_code == 422


def test_ocr_filters_red_marks_and_recognizes_unaccented_fee_scam(client, monkeypatch):
    from app.analyzer.providers import ocr

    image = Image.new("RGB", (240, 180), "white")
    draw = ImageDraw.Draw(image)
    draw.line((0, 0, 239, 179), fill="red", width=2)
    draw.line((0, 179, 239, 0), fill="red", width=2)
    draw.rectangle((30, 80, 40, 82), fill="black")

    def read_media(_mode, data, _settings, **_kwargs):
        with Image.open(io.BytesIO(data)) as prepared:
            assert prepared.getpixel((0, 0)) == (255, 255, 255)
            assert prepared.getpixel((35, 81)) == (0, 0, 0)
        return "Phi dich vu se\nbi tru \"cong 2 gio.\nVui long nhan vao\nh!(ps://ma-... de huy"

    monkeypatch.setattr(ocr, "read_media", read_media)
    response = client.post("/v1/analyze", json=image_body(image))
    assert response.status_code == 200
    result = response.json()
    assert result["risk_level"] == "high"
    assert result["scenario_id"] == "G5.1"
    assert {flag["tactic"] for flag in result["red_flags"]} == {"link", "urgency"}
    assert "url_checks" not in result


def test_periodic_fee_notice_with_official_app_does_not_match_cancellation_link(client):
    result = analyze(client, "Phí dịch vụ sẽ bị trừ trong 2 giờ. Vui lòng mở ứng dụng chính thức để hủy.")
    assert result["risk_level"] == "uncertain"
    assert not any(flag["tactic"] == "link" for flag in result["red_flags"])


def test_real_ocr(client):
    image = Image.new("RGB", (1120, 300), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 38)
    except OSError:
        font = ImageFont.truetype("arial.ttf", 38)
    draw.multiline_text((32, 28), f"Tài khoản tạm giữ\nChuyển ngay qua STK {ACCOUNT}\nKhông được nói với ai", font=font, fill="black", spacing=18)
    response = client.post("/v1/analyze", json=image_body(image))
    assert response.status_code == 200, response.text
    assert response.json()["risk_level"] == "high"
    receipt = client.post("/v1/analyze", json={**image_body(image), "image_kind": "receipt"})
    assert receipt.status_code == 200
    assert receipt.json()["document"]["ocr_boxes"]
    blank = client.post("/v1/analyze", json=image_body(Image.new("RGB", (320, 240), "white")))
    assert blank.status_code == 422


def test_operator_approval_feeds_back_and_report_erasure(client):
    user, ops = login(client, "user"), login(client, "ops")
    assert client.get("/v1/ops/campaigns").status_code == 401
    assert client.get("/v1/ops/campaigns", headers=user).status_code == 403
    result = analyze(client, headers=user)
    campaign_id = report(client, user, result)
    assert report(client, user, result) == campaign_id
    detail = "/v1/ops/campaigns/" + campaign_id
    original = client.get(detail, headers=ops).json()
    assert report(client, user, analyze(client, f"Đổi số mới. Chuyển ngay vào STK {ACCOUNT}")) == campaign_id
    assert not any(row["source"] == "internal_blacklist" for row in analyze(client)["evidence"])
    assert client.post(detail + "/decision", json={"decision": "approve", "revision": original["revision"]}, headers=ops).status_code == 409
    current = client.get(detail, headers=ops).json()
    assert current["report_count"] == 2
    approved = client.post(detail + "/decision", json={"decision": "approve", "revision": current["revision"]}, headers=ops).json()
    assert approved["state"] == "approved"
    assert approved["history"][0]["actor"] == "ops@example.invalid"
    assert any(row["source"] == "internal_blacklist" for row in analyze(client)["evidence"])
    assert client.delete("/v1/me/reports", headers=user).json() == {"deleted": 2}
    assert not any(row["source"] == "internal_blacklist" for row in analyze(client)["evidence"])
    assert len(client.get(detail, headers=ops).json()["history"]) == 1
    assert client.delete("/v1/auth/session", headers=user).status_code == 200
    assert client.get("/v1/auth/me", headers=user).status_code == 401


def test_rejected_campaign_does_not_feed_back(client):
    user, ops = login(client, "user"), login(client, "ops")
    detail = "/v1/ops/campaigns/" + report(client, user, analyze(client))
    case = client.get(detail, headers=ops).json()
    rejected = client.post(detail + "/decision", json={"decision": "reject", "revision": case["revision"]}, headers=ops)
    assert rejected.json()["state"] == "rejected"
    assert not any(row["source"] == "internal_blacklist" for row in analyze(client)["evidence"])


def test_operator_can_correct_group_before_approval(client):
    user, ops = login(client, "user"), login(client, "ops")
    detail = "/v1/ops/campaigns/" + report(client, user, analyze(client))
    first = client.get(detail, headers=ops).json()
    change = {"group": "G4", "revision": first["revision"]}
    assert client.post(detail + "/review", json=change, headers=user).status_code == 403
    edited = client.post(detail + "/review", json=change, headers=ops).json()
    assert edited["group"] == "G4" and edited["state"] == "pending"
    assert edited["history"][0]["action"] == "edit_group"
    assert not any(row["source"] == "internal_blacklist" for row in analyze(client)["evidence"])
    approved = client.post(detail + "/decision",
                           json={"decision": "approve", "revision": edited["revision"]}, headers=ops).json()
    assert approved["group"] == "G4"
    assert [item["action"] for item in approved["history"]] == ["edit_group", "approve"]


@pytest.mark.skipif(not os.getenv("MVP_TEST_POSTGRES_URL"), reason="Requires isolated PostgreSQL with the MVP migration.")
def test_postgres_persists_review(configured):
    configured.database_url = os.environ["MVP_TEST_POSTGRES_URL"]
    with TestClient(create_app(configured)) as postgres:
        user = login(postgres, "user")
        campaign_id = report(postgres, user, analyze(postgres))
        ops = login(postgres, "ops")
        path = "/v1/ops/campaigns/" + campaign_id
        item = postgres.get(path, headers=ops).json()
        sample, = postgres.get(path + "/samples", headers=ops).json()["samples"]
        review = postgres.post(f"{path}/samples/{sample['id']}/review", json={"label": "scam", "revision": 0}, headers=ops)
        assert review.status_code == 200
        decision = {"revision": item["revision"], "decision": "approve"}
        assert postgres.post(path + "/decision", json=decision, headers=ops).status_code == 200
    with TestClient(create_app(configured)) as restarted:
        assert restarted.get(path, headers=ops).json()["state"] == "approved"
        samples = restarted.get("/v1/ops/feedback/samples", headers=ops).json()["samples"]
        assert any(row["id"] == sample["id"] and row["label"] == "scam" for row in samples)
        assert any(item["source"] == "internal_blacklist" for item in analyze(restarted)["evidence"])


def test_share_uses_only_scrubbed_summary(client, monkeypatch):
    user, ops = login(client, "user"), login(client, "ops")
    body = {"analysis_id": analyze(client, headers=user)["analysis_id"]}
    assert client.post("/v1/shares", json=body, headers=ops).status_code == 403
    url = "/v1/shares/" + client.post("/v1/shares", json=body, headers=user).json()["token"]
    shared = client.get(url)
    assert shared.json()["risk"] == "high"
    assert set(shared.json()) == {"risk", "summary", "disclaimer"}
    assert ACCOUNT not in shared.text
    import time
    start = time.time()
    monkeypatch.setattr(time, "time", lambda: start + 86401)
    assert client.get(url).status_code == 404


def test_qr_confirmation_mismatch_crc_and_decode(client):
    import qrcode

    payload = vietqr.build("970436", ACCOUNT, 50000)
    image = qrcode.make(payload).get_image().convert("RGB")
    parsed = client.post("/v1/qr/parse", json=image_body(image)).json()
    assert parsed["risk"] == "low"
    assert parsed["bank"] == "Vietcombank"
    assert parsed["account"] == "••••2345"
    assert client.post("/v1/qr/build", json={"payload": payload}).status_code == 409
    assert client.post("/v1/qr/build", json={"payload": payload, "confirmed": True}).json()["payload"] == payload
    mismatch = {"payload": payload, "text": "Chuyển vào STK 0000067890"}
    assert client.post("/v1/qr/parse", json=mismatch).json()["mismatch"]
    assert client.post("/v1/qr/build", json={**mismatch, "confirmed": True}).status_code == 409
    assert not client.post("/v1/qr/parse", json={"payload": payload[:-1] + ("0" if payload[-1] != "0" else "1")}).json()["valid_crc"]


def test_qwen_fallback_and_domain_lookup_never_send_input(configured, monkeypatch):
    configured.dashscope_api_key = SecretStr("fake-qwen-key")
    configured.safe_browsing_key = "fake"
    calls = []

    def post(url, **kwargs):
        body = kwargs["json"]
        calls.append(body)
        wire = json.dumps(body)
        assert ACCOUNT not in wire
        assert "private-query" not in wire
        request = httpx.Request("POST", url)
        if body.get("model") == "qwen4-max":
            assert url.endswith("/compatible-mode/v1/responses")
            assert kwargs["headers"]["Authorization"] == "Bearer fake-qwen-key"
            return httpx.Response(503, request=request)
        else:
            candidate = body["threatInfo"]["threatEntries"][0]["url"]
            assert candidate == "https://example.com/"
            data = {"matches": [{"threat": {"url": candidate}, "cacheDuration": "300s"}]}
        return httpx.Response(200, request=request, json=data)

    monkeypatch.setattr(httpx, "post", post)
    with TestClient(create_app(configured)) as test_client:
        result = analyze(test_client, TEXT + " https://example.com/private-query")
    assert result["model"] == "rules" and result["degraded"] and result["risk_level"] == "high"
    assert any(item["source"] == "safe_browsing" for item in result["evidence"])
    assert len(calls) == 2


@pytest.mark.parametrize("status", [200, 503])
def test_qwen_responses_provider(configured, monkeypatch, status):
    configured.dashscope_api_key = SecretStr("fake-qwen-key")
    calls = []

    def post(url, **kwargs):
        calls.append(url)
        assert url == "https://ap-southeast-1.maas.qwencloudapi.com/compatible-mode/v1/responses"
        assert kwargs["headers"]["Authorization"] == "Bearer fake-qwen-key"
        body = kwargs["json"]
        assert body["model"] == "qwen4-max"
        assert body["reasoning"] == {"effort": "none"}
        assert body["store"] is False
        assert ACCOUNT not in body["input"] and TEXT not in body["input"]
        assert json.loads(body["input"])["signals"]
        data = {"output": [
            {"type": "reasoning", "summary": []},
            {"type": "message", "content": [
                {"type": "output_text", "text": '{"risk_level":"high","scenario_id":"G1.1"}'},
            ]},
        ]}
        return httpx.Response(status, request=httpx.Request("POST", url), json=data)

    monkeypatch.setattr(httpx, "post", post)
    with TestClient(create_app(configured)) as test_client:
        result = analyze(test_client)
    assert len(calls) == 1
    assert result["risk_level"] == "high"
    assert result["degraded"] is (status == 503)
    if status == 200:
        assert result["model"] == "qwen4-max"


def test_url_gateway_and_qr_link(client):
    raw = "https://mоmо.vn./x?secret=123456789"
    domains = inspect_url(raw)
    assert domains["host"].startswith("xn--")
    assert "brand_homoglyph" in {item["signal"] for item in domains["signals"]}
    response = client.post("/v1/analyze", json={"url": raw})
    assert response.status_code == 200
    assert "secret" not in response.text
    assert response.json()["url_checks"][0]["level"] == "high"
    assert not inspect_url("https://127.0.0.1:8000/")["lookup_allowed"]
    assert inspect_url("https://user@momo.vn/")["level"] == "medium"
    assert client.post("/v1/analyze", json={"url": "file:///tmp/input"}).status_code == 422
    link = client.post("/v1/qr/parse", json={"payload": raw}).json()
    assert link["kind"] == "url" and link["host"] == domains["host"]
    assert client.post("/v1/qr/build", json={"payload": raw, "confirmed": True}).status_code == 409


def test_threat_intel_uses_registered_and_tenant_domains_only(configured, monkeypatch):
    configured.safe_browsing_key = "fake"

    def post(url, **kwargs):
        assert url == "https://safebrowsing.googleapis.com/v4/threatMatches:find"
        assert kwargs["follow_redirects"] is False and kwargs["trust_env"] is False
        entries = kwargs["json"]["threatInfo"]["threatEntries"]
        assert entries == [{"url": "https://example.co.jp/"}, {"url": "https://tenant.github.io/"}]
        data = {"matches": [{"threat": {"url": "https://unrelated.invalid/"}, "cacheDuration": "120s"}]}
        return httpx.Response(200, request=httpx.Request("POST", url), json=data)

    monkeypatch.setattr(httpx, "post", post)
    with TestClient(create_app(configured)) as client:
        result = analyze(client, " ".join(("https://page.example.co.jp/private-path",
                                         "https://app.tenant.github.io/private-path",
                                         "http://127.0.0.1:8020/example", "https://localname.internal/")))
    assert not any(item["source"] == "safe_browsing" and item["weight"] > 0 for item in result["evidence"])
    assert "private-path" not in json.dumps(result)


def test_website_report_uses_source_statuses_and_passive_inputs(client, monkeypatch):
    from app.analyzer.agents import analyze as agent

    monkeypatch.setattr(agent, "read_image", lambda *_: "MoMo\nĐăng nhập\nMật khẩu\nOTP")
    url = "https://momo.vn/?next=private-path-marker"
    html = ('<form action="https://elsewhere.invalid/token"><input type="password" value="private-field-marker">'
            '<input autocomplete="one-time-code"><input autocomplete="cc-number"></form>'
            '<meta http-equiv="refresh" content="5; URL=/next">'
            '<script>document.body.innerHTML = "<input autocomplete=cc-csc>"</script>')
    response = client.post("/v1/analyze", json={"url": url, "website_html": html,
                                                **image_body(Image.new("RGB", (60, 40), "white"))})
    assert response.status_code == 200
    data = response.json()
    report = data["website_report"]
    assert report["sources"] == {"domain": "clear", "community": "clear", "approved_cases": "clear",
                                 "safe_browsing": "unavailable", "rdap": "unavailable"}
    assert report["screenshot"]["credential_labels"] == ["mật khẩu", "mã xác thực"]
    assert report["screenshot"]["brands"] == [{"name": "MoMo", "domain_matches": True}]
    assert report["markup"]["status"] == "checked"
    assert len(report["markup"]["findings"]) == 5
    assert any("chuyển hướng" in hint for hint in data["url_checks"][0]["signals"])
    assert "private-path-marker" not in response.text and "private-field-marker" not in response.text
    assert client.post("/v1/analyze", json={"website_html": html}).status_code == 422
    assert client.post("/v1/analyze", json={"url": "https://momo.vn/", "website_html": html}).json()["risk_level"] == "uncertain"


def test_website_report_distinguishes_official_domain_from_page_review(client):
    response = client.post("/v1/analyze", json={
        "url": "https://www.kaspersky.com.vn/resource-center/preemptive-safety/scam-websites",
    })
    assert response.status_code == 200
    result = response.json()
    assert result["risk_level"] == "uncertain" and result["analysis_path"] == "fast"
    assert result["url_checks"][0]["official_brand"] == "Kaspersky"
    assert result["website_report"]["source_limits"] == {
        "safe_browsing": "Chưa cấu hình", "rdap": "Ngoài phạm vi hỗ trợ",
    }
    assert inspect_url("https://www.kaspersky.com.vn.example/")["official_brand"] is None


def test_website_image_calls_qwen_with_extracted_context_only(configured, monkeypatch):
    from app.analyzer.agents import analyze as agent

    configured.dashscope_api_key = SecretStr("fake-qwen-key")
    monkeypatch.setattr(agent, "read_image", lambda *_: "Mật khẩu\nOTP\nprivate-ocr-marker")
    calls = []

    def post(url, **kwargs):
        body = kwargs["json"]
        assert "private-ocr-marker" not in body["input"] and "private-path-marker" not in body["input"]
        facts = json.loads(body["input"])
        assert facts["website_context"]["credential_labels"] == ["mật khẩu", "mã xác thực"]
        assert facts["website_context"]["has_screenshot"] is True
        calls.append(url)
        return httpx.Response(200, request=httpx.Request("POST", url), json={"output": [
            {"type": "message", "content": [{"type": "output_text", "text": '{"risk_level":"high","scenario_id":"G5.4"}'}]},
        ]})

    monkeypatch.setattr(httpx, "post", post)
    with TestClient(create_app(configured)) as client:
        response = client.post("/v1/analyze", json={"url": "https://example.com/private-path-marker",
                                                     "website_preview": True,
                                                     **image_body(Image.new("RGB", (60, 40), "white"))})
    assert response.status_code == 200 and len(calls) == 1
    result = response.json()
    assert result["analysis_path"] == "deep" and result["model"] == "qwen4-max"
    assert result["risk_level"] == "uncertain" and result["scenario_id"] is None


def test_public_article_preview_checks_exact_url_and_requires_consistent_evidence(client, monkeypatch):
    from app.evidence import public_article

    target = public_article.ARTICLE_URL
    cover = public_article.COVER_URL
    html = (f'<link rel="canonical" href="{target}"><meta property="og:type" content="article">'
            f'<meta property="og:image" content="{cover}"><article><h1>Website lừa đảo</h1>'
            '<h2>Cách nhận biết website giả</h2><h2>Báo cáo website</h2></article>')
    requested = []

    def read_bytes(url, _types, _size):
        assert url in {target, cover}
        requested.append(url)
        if url == target:
            return html.encode()
        image = io.BytesIO()
        Image.new("RGB", (32, 32), "pink").save(image, format="WEBP")
        return image.getvalue()

    def qwen(_settings, _limits, _template, facts):
        assert all(isinstance(value, bool) for value in facts.values())
        return {"context": "educational"}, "ok"

    monkeypatch.setattr(public_article, "read_bytes", read_bytes)
    monkeypatch.setattr(public_article, "query_qwen", qwen)
    public_article._snapshot.cache_clear()
    try:
        wrong = client.post("/v1/analyze", json={"url": target + "?private=1", "website_preview": True}).json()
        assert "article" not in wrong["website_report"] and not requested
        result = client.post("/v1/analyze", json={"url": target, "website_preview": True}).json()
        assert requested == [target, cover] and result["model"] == "qwen4-max"
        assert result["risk_level"] == "low" and result["analysis_path"] == "deep"
        assert result["website_report"]["article"]["image_webp"]
        html = html.replace("</article>", '<form><input type="password"></form></article>')
        public_article._snapshot.cache_clear()
        result = client.post("/v1/analyze", json={"url": target, "website_preview": True}).json()
        assert result["risk_level"] == "uncertain"
        assert result["website_report"]["article"]["context"] == "uncertain"
    finally:
        public_article._snapshot.cache_clear()


def test_community_blocklist_is_separate_from_an_approved_case(client, monkeypatch):
    from app.analyzer.agents import analyze as agent
    from app.qr import checks

    def example_match(host):
        return host if host == "example.org" else None

    monkeypatch.setattr(agent, "community_domain_match", example_match)
    monkeypatch.setattr(checks, "community_domain_match", example_match)
    result = analyze(client, "https://example.org/")
    assert result["risk_level"] == "medium"
    assert [(item["source"], item["weight"]) for item in result["evidence"]] == [("external_blacklist", 45)]
    qr = client.post("/v1/qr/parse", json={"payload": "https://example.org/"}).json()
    assert qr["risk"] == "medium" and not qr["confirmed_alert"]
    assert any("danh sách" in signal.lower() for signal in qr["signals"])


def test_routing_requires_an_actual_signal_and_keeps_checks_separate(configured, monkeypatch):
    from app.analyzer.agents import analyze as agent

    def unused(*_args, **_kwargs):
        pytest.fail("Qwen should be skipped without decision-relevant signals")

    monkeypatch.setattr(agent, "infer", unused)
    with TestClient(create_app(configured)) as client:
        result = analyze(client, "Xin trao đổi thêm")
        assert (result["risk_level"], result["analysis_path"], result["risk_score"]) == ("uncertain", "fast", 0)
        cases = [
            ({"url": "https://momo.vn/"}, "low"),
            ({"qr_payload": "https://momo.vn/"}, "low"),
            ({"url": "https://momo.vn/abc?redirect=demo"}, "uncertain"),
            ({"url": "https://momo.vn/", "qr_payload": "https://momo.vn/abc"}, "uncertain"),
            ({"text": "https://momo.vn/"}, "low"),
            ({"text": "Bạn xem nội dung ở https://momo.vn/"}, "uncertain"),
            ({"qr_payload": vietqr.build("970436", ACCOUNT, 50000)}, "low"),
        ]
        for body, risk in cases:
            response = client.post("/v1/analyze", json=body)
            assert response.status_code == 200
            assert response.json()["risk_level"] == risk
        qr_link = client.post("/v1/qr/parse", json={"payload": "https://momo.vn/"}).json()
        assert qr_link["kind"] == "url" and qr_link["risk"] == "low"
        assert client.post("/v1/qr/build", json={"payload": "https://momo.vn/", "confirmed": True}).status_code == 409


def test_official_homepage_does_not_override_threat_intelligence(client, monkeypatch):
    from app.evidence.safe_browsing import SafeBrowsing

    monkeypatch.setattr(SafeBrowsing, "lookup", lambda _self, _domains: (True, True))
    url = "https://momo.vn/"
    analysis = client.post("/v1/analyze", json={"url": url}).json()
    assert analysis["risk_level"] == "high"
    qr_link = client.post("/v1/qr/parse", json={"payload": url}).json()
    assert qr_link["risk"] == "high" and qr_link["threat_intel_match"]


def test_fraud_url_benchmark_artifact_cannot_be_enabled(configured, tmp_path):
    (tmp_path / "manifest.json").write_text('{"stage":"benchmark_only"}', encoding="utf-8")
    configured.fraud_url_model_path = str(tmp_path / "fraud-url-v1.txt")
    with pytest.raises(ValueError, match="Benchmark-only"):
        create_app(configured)


def test_rdap_uses_only_registry_and_domain(configured, monkeypatch):
    configured.rdap_lookups_per_hour = 1
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        assert url == "https://rdap.verisign.com/com/v1/domain/momo-verify-example.com"
        assert kwargs["follow_redirects"] is False
        created = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        return httpx.Response(200, request=httpx.Request("GET", url),
                              json={"events": [{"eventAction": "registration", "eventDate": created}]})

    monkeypatch.setattr(httpx, "get", get)
    with TestClient(create_app(configured)) as client:
        url = "https://momo-verify-example.com/private-documents?token=demo"
        result = analyze(client, url)
        assert result["url_checks"][0]["domain_age_days"] == 7
        assert any(row["source"] == "rdap" for row in result["evidence"])
        assert analyze(client, url)["url_checks"][0]["domain_age_days"] is None
    assert len(calls) == 1


def test_website_check_gets_registration_without_opening_unlisted_page(configured, monkeypatch):
    from app.analyzer.agents import analyze as agent

    configured.rdap_lookups_per_hour = 2

    def registry(url, **kwargs):
        assert url == "https://rdap.verisign.com/com/v1/domain/example.com"
        assert kwargs["follow_redirects"] is False and kwargs["trust_env"] is False
        return httpx.Response(200, request=httpx.Request("GET", url), json={"events": [
            {"eventAction": "registration", "eventDate": "2000-01-02T13:00:00Z"},
        ]})

    monkeypatch.setattr(httpx, "get", registry)
    monkeypatch.setattr(agent, "PUBLIC_ARTICLES", {})
    with TestClient(create_app(configured)) as client:
        result = client.post("/v1/analyze", json={"url": "https://example.com/private-path?token=example",
                                                  "website_preview": True}).json()
    assert result["website_report"]["capture_scope"] == "unlisted"
    assert "article" not in result["website_report"]
    assert result["website_report"]["sources"]["rdap"] == "checked"
    assert result["url_checks"][0]["domain_registered_on"] == "2000-01-02"
    assert result["risk_level"] == "uncertain"


def test_receipt_regions_and_unverified_transaction(client, monkeypatch):
    from app.analyzer.providers import ocr

    text = "Giao dịch thành công 125.000 VND"
    tsv = "level\tleft\ttop\twidth\theight\ttext\n5\t25\t10\t50\t20\t" + text

    def recognize(operation, *_args, **_kwargs):
        assert operation == "ocr-tsv"
        return tsv

    monkeypatch.setattr(ocr, "read_media", recognize)
    payload = {**image_body(Image.new("RGB", (100, 100), "white")), "image_kind": "receipt"}
    result = client.post("/v1/analyze", json=payload).json()
    VALIDATOR.validate(result)
    document = result["document"]
    assert document["ocr_boxes"] == [[0.25, 0.1, 0.5, 0.2]]
    assert document["transaction_status"] == "unverified"
    assert {item["category"] for item in document["signals"]} == {"physical", "visual", "semantic"}


def test_speech_ingestion_and_local_transcription(configured, monkeypatch):
    from pathlib import Path
    from app.analyzer.providers import speech

    data = io.BytesIO()
    with wave.open(data, "wb") as clip:
        clip.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        clip.writeframes(bytes(32_000))
    body = {"audio_base64": base64.b64encode(data.getvalue()).decode()}
    with TestClient(create_app(configured)) as client:
        assert client.post("/v1/analyze", json=body).status_code == 503
        assert client.post("/v1/analyze", json={"audio_base64": "invalid"}).status_code == 422

    configured.whisper_command = "whisper-cli"
    configured.whisper_model_path = "test-model.bin"
    calls = []

    def run(command, **_kwargs):
        source = Path(command[-1])
        assert source.read_bytes() == data.getvalue()
        source.with_suffix(".txt").write_text(TEXT, encoding="utf-8")
        calls.append(source)

    monkeypatch.setattr(speech.subprocess, "run", run)
    with TestClient(create_app(configured)) as client:
        response = client.post("/v1/analyze", json=body)
        assert response.status_code == 200
        assert response.json()["risk_level"] == "high"
    assert len(calls) == 1 and not calls[0].exists()


def test_split_preserves_review_history_and_keeps_campaigns_separate(client):
    user, ops = login(client, "user"), login(client, "ops")
    campaign = report(client, user, analyze(client))
    assert report(client, user, analyze(client)) == campaign
    path = f"/v1/ops/campaigns/{campaign}"
    original = client.get(path, headers=ops).json()
    sample = client.get(path + "/samples", headers=ops).json()["samples"][0]
    sample_path = f"{path}/samples/{sample['id']}"
    assert client.post(sample_path + "/review", json={"label": "scam", "revision": 0}, headers=ops).status_code == 200
    body = {"revision": original["revision"]}
    assert client.post(sample_path + "/split", json=body, headers=user).status_code == 403
    response = client.post(sample_path + "/split", json=body, headers=ops)
    assert response.status_code == 200
    separate = response.json()["campaign_id"]
    assert separate != campaign
    assert client.post(sample_path + "/split", json=body, headers=ops).status_code == 409
    report(client, user, analyze(client))
    rows = client.get("/v1/ops/campaigns?state=pending", headers=ops).json()
    assert {row["id"] for row in rows} == {campaign, separate}
    assert sum(row["report_count"] for row in rows) == 3
    exported, = client.get("/v1/ops/feedback/samples", headers=ops).json()["samples"]
    assert exported["group_id"] == separate


def test_ops_sample_labels_and_alerts_require_independent_review(client):
    user = login(client, "user")
    ops = login(client, "ops")
    result = analyze(client)
    campaign = report(client, user, result)
    path = f"/v1/ops/campaigns/{campaign}"
    samples = path + "/samples"
    assert client.get(samples, headers=user).status_code == 403
    assert client.get("/v1/ops/overview", headers=user).status_code == 403
    assert client.get("/v1/ops/system", headers=user).status_code == 403
    assert client.get("/v1/ops/system", headers=ops).json()["qwen_model"] is None
    assert client.get("/v1/ops/overview", headers=ops).json()["reports_24h"] == 1
    sample, = client.get(samples, headers=ops).json()["samples"]
    assert sample["inputs"] == ["text"] and ACCOUNT not in str(sample)
    label = f"{samples}/{sample['id']}/review"
    assert client.post(label, json={"label": "scam", "revision": 0}, headers=user).status_code == 403
    assert client.post(label, json={"label": "scam", "revision": 0}, headers=ops).json()["revision"] == 1
    export = "/v1/ops/feedback/samples"
    assert client.get(export, headers=user).status_code == 403
    exported, = client.get(export, headers=ops).json()["samples"]
    assert exported["group_id"] == campaign and exported["label"] == "scam"
    assert ACCOUNT not in str(exported) and "actor" not in exported
    assert client.post(label, json={"label": "legit", "revision": 0}, headers=ops).status_code == 409
    assert client.post(label, json={"label": "withdrawn", "revision": 1}, headers=ops).json()["revision"] == 2
    history = client.get(samples, headers=ops).json()["samples"][0]["history"]
    assert client.get(export, headers=ops).json()["samples"] == []
    assert [item["label"] for item in history] == ["scam", "withdrawn"]
    detail = client.get(path, headers=ops).json()
    assert all(row["state"] == "preview" for row in detail["alerts"]["channels"])
    assert client.post(path + "/decision", headers=ops,
                       json={"decision": "approve", "revision": detail["revision"]}).status_code == 200
    alerts = client.get(path, headers=ops).json()["alerts"]
    assert alerts["transaction_status"] == "unverified"
    assert [row["id"] for row in alerts["channels"] if row["state"] == "published"] == ["web"]
    assert client.delete("/v1/me/reports", headers=user).json()["deleted"] == 1
    assert client.get(samples, headers=ops).json()["samples"] == []
    assert all(row["state"] == "preview" for row in client.get(path, headers=ops).json()["alerts"]["channels"])


def test_investigation_graph_and_verified_feedback(client):
    user, ops = login(client, "user"), login(client, "ops")
    campaign = report(client, user, analyze(client))
    detail_url = "/v1/ops/campaigns/" + campaign
    assert client.get(detail_url, headers=user).status_code == 403
    assert client.get("/v1/ops/feedback", headers=user).status_code == 403
    assert client.get("/v1/ops/feedback", headers=ops).json()["samples"] == []
    detail = client.get(detail_url, headers=ops)
    assert ACCOUNT not in detail.text
    workspace = detail.json()["workspace"]
    assert workspace["permission"] == "draft_only"
    assert workspace["supervisor_review"]["status"] == "disabled"
    assert workspace["report"]["approval_required"] is True
    assert any(edge["from"] == "entity-ACCOUNT" and edge["to"] == "input-text"
               for edge in workspace["investigation"]["edges"])
    assert analyze(client)["model"] == "rules"
    assert not any(item["source"] == "internal_blacklist" for item in analyze(client)["evidence"])
    decision = client.post(detail_url + "/decision", headers=ops,
                           json={"decision": "approve", "revision": detail.json()["revision"]})
    assert decision.status_code == 200
    samples = client.get("/v1/ops/feedback", headers=ops).json()["samples"]
    assert [(item["campaign_id"], item["review_label"]) for item in samples] == [(campaign, "approved_campaign")]
    related_campaign = report(client, user, analyze(client))
    related = client.get("/v1/ops/campaigns/" + related_campaign, headers=ops).json()["workspace"]
    assert related["threat_intel"]["confirmed_related_campaigns"] == [campaign]


def test_all_workspace_agents_use_qwen_without_sending_case_identifiers(configured, monkeypatch):
    configured.dashscope_api_key = SecretStr("fake-qwen-key")
    requests = {}

    def post(url, **kwargs):
        assert url == "https://ap-southeast-1.maas.qwencloudapi.com/compatible-mode/v1/responses"
        body = kwargs["json"]
        assert kwargs["follow_redirects"] is False and kwargs["trust_env"] is False
        assert body["model"] == "qwen4-max" and body["store"] is False
        facts = json.loads(body["input"])
        agent = facts.get("agent")
        content = {"risk_level": "high", "scenario_id": "G1.1"}
        if agent:
            requests[agent] = body["input"]
            assert facts["permission"] == "draft_only"
            assert "signals" not in facts["facts"]
            content = {"code": next(iter(facts["options"]))}
            if agent == "protection":
                content["action"] = "approve"
        return httpx.Response(200, request=httpx.Request("POST", url), json={"output": [
            {"type": "message", "content": [{"type": "output_text", "text": json.dumps(content)}]},
        ]})

    monkeypatch.setattr(httpx, "post", post)
    with TestClient(create_app(configured)) as client:
        user, ops = login(client, "user"), login(client, "ops")
        campaign_id = report(client, user, analyze(client))
        path = "/v1/ops/campaigns/" + campaign_id
        assert client.get(path, headers=user).status_code == 403
        assert not requests
        detail = client.get(path, headers=ops).json()
        assert detail["state"] == "pending"
        workspace = detail["workspace"]
        assert workspace["permission"] == "draft_only"
        assert workspace["report"]["approval_required"] is True
        assert workspace["supervisor_review"]["status"] == "ok"
        agents = {"detection", "threat_intel", "forensics", "investigation", "protection", "report"}
        assert requests.keys() == agents | {"supervisor"}
        assert all(ACCOUNT not in payload and campaign_id not in payload for payload in requests.values())
        assert all(workspace[agent]["review"]["model"] == "qwen4-max" for agent in agents - {"protection"})
        assert workspace["protection"]["review"] == {"status": "invalid", "model": None, "note": None}
        assert workspace["protection"]["recommendations"]
