from fastapi.testclient import TestClient

from app.main import create_app
from conftest import assert_error, make_settings


def test_health_returns_status_and_version(tmp_path):
    client = TestClient(create_app(make_settings(tmp_path, app_version="abc1234")))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "abc1234"}


def test_health_default_version(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["version"]


def test_unknown_route_is_vietnamese_json(client):
    assert_error(client.get("/khong-co"), 404, "not_found")


def test_wrong_method_is_vietnamese_json(client):
    assert_error(client.get("/v1/analyze"), 405, "method_not_allowed")


def test_unhandled_exception_returns_vietnamese_500(app):
    def boom():
        raise RuntimeError("chi tiet noi bo 0912345678")

    app.add_api_route("/boom", boom)
    body = assert_error(TestClient(app, raise_server_exceptions=False).get("/boom"), 500, "internal_error")
    assert "0912345678" not in str(body)
