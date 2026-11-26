import base64
import io
import json
import os

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

from app.analyzer.contract import VALIDATOR
from app.config import Settings
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
        llm_base_url="", llm_model="", safe_browsing_key="",
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
    configured.llm_model = "primary"
    configured.llm_fallback_model = "fallback"
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
