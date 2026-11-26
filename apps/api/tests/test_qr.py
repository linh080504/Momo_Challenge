import pytest

from app.core.config import DEFAULT_VIETQR_PATH
from app.qr import _load_vietqr
from conftest import assert_error

vietqr = _load_vietqr(str(DEFAULT_VIETQR_PATH))  # chính module skill, dùng để dựng dữ liệu thử


def test_parse_valid_dynamic_qr(client):
    payload = vietqr.build("970436", "0123456789", 50000, "TKC 123")
    response = client.post("/v1/qr/parse", json={"payload": payload})
    assert response.status_code == 200
    body = response.json()
    assert body["valid_crc"] is True and body["is_napas"] is True
    assert body["bank_bin"] == "970436" and body["bank_name"] == "Vietcombank"
    assert body["account"] == "0123456789" and body["amount"] == "50000"
    assert body["note"] == "TKC 123" and body["initiation"] == "dynamic"
    assert body["currency"] == "704" and body["country"] == "VN"
    assert body["warnings"] == []


def test_parse_static_qr_without_amount(client):
    body = client.post("/v1/qr/parse", json={"payload": vietqr.build("970422", "9876543210")}).json()
    assert body["initiation"] == "static" and body["amount"] is None and body["bank_name"] == "MB Bank"


def test_tampered_qr_reports_bad_crc(client):
    payload = vietqr.build("970436", "0123456789", 50000).replace("0123456789", "0987654321")
    response = client.post("/v1/qr/parse", json={"payload": payload})
    assert response.status_code == 200
    body = response.json()
    assert body["valid_crc"] is False
    assert any("CRC" in w for w in body["warnings"])


def test_unknown_bank_bin_is_warned_not_failed(client):
    body = client.post("/v1/qr/parse", json={"payload": vietqr.build("970499", "123456789")}).json()
    assert body["bank_name"] is None and any("970499" in w for w in body["warnings"])


def test_non_napas_tlv_is_200_with_warning(client):
    body = client.post("/v1/qr/parse", json={"payload": "000201010211"}).json()
    assert body["is_napas"] is False and any("NAPAS" in w for w in body["warnings"])


@pytest.mark.parametrize("payload", ["xin chào, đây không phải mã QR", "00020101021138", "0002"])
def test_garbage_payload_is_422_vietnamese(client, payload):
    assert_error(client.post("/v1/qr/parse", json={"payload": payload}), 422, "invalid_qr")


@pytest.mark.parametrize("body", [{}, {"payload": ""}, {"payload": "x" * 5000}, {"payload": 123}])
def test_invalid_request_is_422(client, body):
    assert_error(client.post("/v1/qr/parse", json=body), 422, "validation_error")
