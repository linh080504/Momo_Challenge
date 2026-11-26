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
        llm_base_url="", llm_model="", llm_fallback_model="", dashscope_api_key="", safe_browsing_key="",
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
    result = analyze(client)
    assert result["risk_level"] == "high"
    assert result["degraded"] is True
    assert len(result["red_flags"]) == 3
    assert all(flag["quote"] in TEXT for flag in result["red_flags"])
    assert ACCOUNT not in json.dumps(result)
    assert analyze(client, "Mẹ ơi tối con về ăn cơm nhé")["risk_level"] == "low"
    assert analyze(client, "Vui lòng không cung cấp mã OTP cho ai")["risk_level"] == "low"
    assert analyze(client, "Xin trao đổi thêm")["risk_level"] == "uncertain"


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


def test_public_input_contract_and_qr_result_variants(client):
    paths = client.get("/openapi.json").json()["paths"]
    ask = paths["/v1/analyze"]["post"]
    stream = paths["/v1/analyze/stream"]["post"]
    parse = paths["/v1/qr/parse"]["post"]
    inputs = ask["requestBody"]["content"]["application/json"]["schema"]["properties"]
    assert set(inputs) == {"text", "image_base64", "image_mime", "image_kind", "audio_base64", "qr_payload", "url", "locale"}
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
        decision = {"revision": item["revision"], "decision": "approve"}
        assert postgres.post(path + "/decision", json=decision, headers=ops).status_code == 200
    with TestClient(create_app(configured)) as restarted:
        assert restarted.get(path, headers=ops).json()["state"] == "approved"
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


def test_model_fallback_and_domain_lookup_never_send_input(configured, monkeypatch):
    configured.llm_base_url = "https://llm.example.invalid/v1"
    configured.llm_api_key = "fake-chat-key"
    configured.llm_model = "primary"
    configured.llm_fallback_model = "fallback"
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
        if url.startswith(configured.llm_base_url):
            assert kwargs["headers"]["Authorization"] == "Bearer fake-chat-key"
            if body["model"] == "primary":
                return httpx.Response(503, request=request)
            data = {"choices": [{"message": {"content": '{"risk_level":"high","scenario_id":"G5.1"}'}}]}
        else:
            candidate = body["threatInfo"]["threatEntries"][0]["url"]
            assert candidate == "https://example.com/"
            data = {"matches": [{"threat": {"url": candidate}, "cacheDuration": "300s"}]}
        return httpx.Response(200, request=request, json=data)

    monkeypatch.setattr(httpx, "post", post)
    with TestClient(create_app(configured)) as test_client:
        result = analyze(test_client, TEXT + " https://example.com/private-query")
    assert result["model"] == "fallback" and not result["degraded"]
    assert any(item["source"] == "safe_browsing" for item in result["evidence"])
    assert len(calls) == 3


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


def test_community_blocklist_is_separate_from_an_approved_case(client, monkeypatch):
    from app.analyzer.agents import analyze as agent

    monkeypatch.setattr(agent, "community_domain_match", lambda host: host if host == "example.org" else None)
    result = analyze(client, "https://example.org/")
    assert result["risk_level"] == "medium"
    assert [(item["source"], item["weight"]) for item in result["evidence"]] == [("external_blacklist", 45)]


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
