import copy
import logging
import sys

import pytest
from fastapi.testclient import TestClient

from app.day_two import create_app
from conftest import (SAMPLE_RESULT, AnalyzerError, FakeAnalyzer, assert_error, b64, make_jpeg, make_png,
                      make_settings)

MAX = 5 * 1024 * 1024
TEXT = "Tôi là cán bộ công an, anh chuyển tiền vào tài khoản tạm giữ để xác minh, không được nói với ai."


# ---------- 200: văn bản / ảnh ----------

def test_text_returns_analyzer_result_unchanged(client, fake_analyzer):
    response = client.post("/v1/analyze", json={"text": TEXT})
    assert response.status_code == 200
    assert response.json() == SAMPLE_RESULT
    assert fake_analyzer.calls == [(TEXT, None, None)]


def test_png_image_is_decoded_and_forwarded(client, fake_analyzer):
    png = make_png()
    response = client.post("/v1/analyze", json={"text": "", "image_base64": b64(png), "image_mime": "image/png"})
    assert response.status_code == 200
    assert fake_analyzer.calls == [(None, png, "image/png")]


def test_jpeg_with_text_forwards_both(client, fake_analyzer):
    jpeg = make_jpeg()
    response = client.post("/v1/analyze", json={"text": TEXT, "image_base64": b64(jpeg), "image_mime": "image/jpeg"})
    assert response.status_code == 200
    assert fake_analyzer.calls == [(TEXT, jpeg, "image/jpeg")]


def test_image_exactly_5mb_is_accepted(client, fake_analyzer):
    png = make_png()
    png += b"\0" * (MAX - len(png))
    assert len(png) == MAX
    response = client.post("/v1/analyze", json={"image_base64": b64(png), "image_mime": "image/png"})
    assert response.status_code == 200


def test_locale_is_optional_and_url_is_accepted_but_unused(client, fake_analyzer):
    assert client.post("/v1/analyze", json={"text": TEXT}).status_code == 200
    assert client.post("/v1/analyze", json={"text": TEXT, "locale": None}).status_code == 200
    response = client.post("/v1/analyze", json={"text": TEXT, "locale": "vi", "url": "https://x.example", "extra": 1})
    assert response.status_code == 200
    assert fake_analyzer.calls[-1] == (TEXT, None, None)  # url không ảnh hưởng đầu vào analyzer


def test_json_body_with_utf8_bom_is_accepted(client, fake_analyzer):
    """PowerShell 5.1 `Set-Content -Encoding utf8` ghi BOM; docs/RUN_LOCAL.md hướng dẫn cách đó."""
    body = b"\xef\xbb\xbf" + '{"text": "Chuyển tiền gấp cho công an"}'.encode("utf-8")
    response = client.post("/v1/analyze", content=body, headers={"Content-Type": "application/json"})
    assert response.status_code == 200
    assert fake_analyzer.calls[0][0] == "Chuyển tiền gấp cho công an"


def test_sync_analyzer_function_is_supported(client, monkeypatch):
    fake = FakeAnalyzer().install(monkeypatch, sync=True)
    assert client.post("/v1/analyze", json={"text": TEXT}).status_code == 200
    assert len(fake.calls) == 1


def test_mime_is_case_insensitive(client, fake_analyzer):
    response = client.post("/v1/analyze", json={"image_base64": b64(make_png()), "image_mime": "IMAGE/PNG"})
    assert response.status_code == 200
    assert fake_analyzer.calls[0][2] == "image/png"


# ---------- 422: thiếu đầu vào ----------

@pytest.mark.parametrize("payload", [
    {}, {"text": ""}, {"text": "   \n"}, {"text": None}, {"image_base64": "", "image_mime": "image/png"},
])
def test_missing_both_inputs_is_422(client, fake_analyzer, payload):
    assert_error(client.post("/v1/analyze", json=payload), 422, "missing_input")
    assert fake_analyzer.calls == []


def test_image_without_mime_is_422(client, fake_analyzer):
    assert_error(client.post("/v1/analyze", json={"image_base64": b64(make_png())}), 422, "missing_image_mime")


def test_wrong_field_type_is_422_and_does_not_echo_input(client, fake_analyzer):
    body = assert_error(client.post("/v1/analyze", json={"text": 12345678901}), 422, "validation_error")
    assert body["fields"] == ["text"] and "12345678901" not in str(body)


def test_invalid_json_is_422(client, fake_analyzer):
    response = client.post("/v1/analyze", content="{không phải json", headers={"Content-Type": "application/json"})
    assert_error(response, 422, "validation_error")


def test_text_too_long_is_422(tmp_path, monkeypatch):
    fake = FakeAnalyzer().install(monkeypatch)
    client = TestClient(create_app(make_settings(tmp_path, max_text_chars=50)))
    assert_error(client.post("/v1/analyze", json={"text": "a" * 51}), 422, "text_too_long")
    assert fake.calls == []


# ---------- 415: sai định dạng / ảnh hỏng ----------

@pytest.mark.parametrize("mime", ["image/gif", "image/webp", "application/pdf", "image/jpg", "text/plain"])
def test_unsupported_mime_is_415(client, fake_analyzer, mime):
    response = client.post("/v1/analyze", json={"image_base64": b64(make_png()), "image_mime": mime})
    assert_error(response, 415, "unsupported_image_type")
    assert fake_analyzer.calls == []


@pytest.mark.parametrize("bad", ["@@@ không phải base64 @@@", "abc", "data:image/png;base64," + b64(make_png())])
def test_corrupt_base64_is_415(client, fake_analyzer, bad):
    assert_error(client.post("/v1/analyze", json={"image_base64": bad, "image_mime": "image/png"}), 415, "invalid_image")
    assert fake_analyzer.calls == []


def test_declared_mime_not_matching_bytes_is_415(client, fake_analyzer):
    response = client.post("/v1/analyze", json={"image_base64": b64(make_jpeg()), "image_mime": "image/png"})
    assert_error(response, 415, "invalid_image")
    response = client.post("/v1/analyze", json={"image_base64": b64(make_png()), "image_mime": "image/jpeg"})
    assert_error(response, 415, "invalid_image")


def test_gif_bytes_declared_as_png_is_415(client, fake_analyzer):
    gif = b"GIF89a" + b"\0" * 64
    assert_error(client.post("/v1/analyze", json={"image_base64": b64(gif), "image_mime": "image/png"}), 415)


def test_truncated_png_is_415(client, fake_analyzer):
    assert_error(client.post("/v1/analyze", json={"image_base64": b64(make_png()[:20]), "image_mime": "image/png"}), 415)


def test_empty_decoded_image_is_415(client, fake_analyzer):
    assert_error(client.post("/v1/analyze", json={"image_base64": "====", "image_mime": "image/png"}), 415)


# ---------- 413: quá cỡ ----------

def test_image_one_byte_over_5mb_is_413(client, fake_analyzer):
    png = make_png()
    png += b"\0" * (MAX + 1 - len(png))
    body = assert_error(client.post("/v1/analyze", json={"image_base64": b64(png), "image_mime": "image/png"}),
                        413, "image_too_large")
    assert "5 MB" in body["error"]
    assert fake_analyzer.calls == []


def test_6mb_image_is_413(client, fake_analyzer):
    png = make_png(extra=6 * 1024 * 1024)
    response = client.post("/v1/analyze", json={"image_base64": b64(png), "image_mime": "image/png"})
    assert_error(response, 413)
    assert fake_analyzer.calls == []


def test_oversized_base64_rejected_before_decoding(tmp_path, fake_analyzer):
    client = TestClient(create_app(make_settings(tmp_path, max_body_bytes=50 * 1024 * 1024)))
    huge = "A" * (8 * 1024 * 1024)
    assert_error(client.post("/v1/analyze", json={"image_base64": huge, "image_mime": "image/gif"}), 413, "image_too_large")


# ---------- 502: analyzer lỗi — không bao giờ trả `low` ----------

def test_analyzer_error_maps_to_502_without_leaking_message(client, fake_analyzer):
    fake_analyzer.error = AnalyzerError("llm_timeout", "chi tiet noi bo: khoa API sk-123")
    body = assert_error(client.post("/v1/analyze", json={"text": TEXT}), 502, "llm_timeout")
    assert "sk-123" not in str(body)


@pytest.mark.parametrize("code,status", [("empty_input", 422), ("unsupported_mime", 415), ("image_too_large", 413)])
def test_analyzer_input_errors_map_to_4xx_not_502(client, fake_analyzer, code, status):
    fake_analyzer.error = AnalyzerError(code, "chi tiet noi bo cua analyzer: 0123456789")
    body = assert_error(client.post("/v1/analyze", json={"text": TEXT}), status, code)
    assert "chi tiet noi bo" not in str(body) and "0123456789" not in str(body)  # message BE cố định, không chuyển tiếp


def test_other_analyzer_codes_stay_502(client, fake_analyzer):
    for code in ("llm_error", "llm_timeout", "invalid_output"):
        fake_analyzer.error = AnalyzerError(code, "x")
        assert_error(client.post("/v1/analyze", json={"text": TEXT}), 502, code)


def test_analyzer_error_with_unsafe_code_gets_generic_code(client, fake_analyzer):
    fake_analyzer.error = AnalyzerError("Có Lỗi!! <script>", "x")
    assert_error(client.post("/v1/analyze", json={"text": TEXT}), 502, "analyzer_error")


def test_unexpected_analyzer_exception_maps_to_502(client, fake_analyzer):
    fake_analyzer.error = RuntimeError("boom")
    assert_error(client.post("/v1/analyze", json={"text": TEXT}), 502, "analyzer_error")


def test_analyzer_timeout_maps_to_502(tmp_path, monkeypatch):
    fake = FakeAnalyzer().install(monkeypatch)
    fake.delay = 1.0
    client = TestClient(create_app(make_settings(tmp_path, analyze_timeout_s=0.05)))
    assert_error(client.post("/v1/analyze", json={"text": TEXT}), 502, "analyzer_timeout")


def test_missing_analyzer_module_maps_to_502(client, monkeypatch):
    monkeypatch.setitem(sys.modules, "app.analyzer", None)  # import → ImportError
    assert_error(client.post("/v1/analyze", json={"text": TEXT}), 502, "analyzer_unavailable")


def test_analyzer_returning_non_dict_is_502(client, fake_analyzer):
    fake_analyzer.result = ["không phải dict"]
    assert_error(client.post("/v1/analyze", json={"text": TEXT}), 502, "invalid_analyzer_output")


@pytest.mark.parametrize("mutate", [
    lambda r: r.pop("ai_disclaimer"),
    lambda r: r.update(ai_disclaimer="Kết quả chắc chắn đúng."),
    lambda r: r.update(risk_level="safe"),
    lambda r: r.update(risk_score=101),
    lambda r: r.update(scenario_group="G9"),
    lambda r: r.update(summary="x" * 281),
    lambda r: r.update(red_flags=[{"quote": "chỉ có quote"}] * 1),
    lambda r: r.update(verification_questions=["1", "2", "3", "4"]),
    lambda r: r.update(recommended_action="transfer_money"),
])
def test_output_violating_schema_is_never_returned(client, fake_analyzer, mutate):
    result = copy.deepcopy(SAMPLE_RESULT)
    mutate(result)
    fake_analyzer.result = result
    assert_error(client.post("/v1/analyze", json={"text": TEXT}), 502, "invalid_analyzer_output")


# ---------- không log PII ----------

def test_logs_never_contain_user_text_or_analyzer_message(client, fake_analyzer, caplog):
    caplog.set_level(logging.DEBUG)
    secret_text = "Chuyển vào STK 0123456789, gọi 0912345678 gấp"
    client.post("/v1/analyze", json={"text": secret_text})
    fake_analyzer.error = AnalyzerError("llm_error", "lỗi khi xử lý 0123456789")
    client.post("/v1/analyze", json={"text": secret_text})
    fake_analyzer.result = {"risk_level": "low", "summary": "0912345678"}
    fake_analyzer.error = None
    client.post("/v1/analyze", json={"text": secret_text})
    assert "0123456789" not in caplog.text and "0912345678" not in caplog.text
    assert caplog.text  # có log thật, không phải log rỗng
