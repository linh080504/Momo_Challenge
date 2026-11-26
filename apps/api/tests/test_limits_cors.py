"""Rate limit theo IP, CORS cho localhost:3000, giới hạn dung lượng body."""
import asyncio

from fastapi.testclient import TestClient

from app.core.middleware import SlidingWindowLimiter
from app.day_two import create_app
from conftest import assert_error, make_settings

ORIGIN = "http://localhost:3000"
TEXT = {"text": "Chuyển tiền gấp cho công an"}


# ---------- bộ giới hạn ----------

def test_limiter_sliding_window_with_fake_clock():
    now = [100.0]
    limiter = SlidingWindowLimiter(clock=lambda: now[0])
    assert [limiter.hit("a", 2, 60) for _ in range(2)] == [0.0, 0.0]
    wait = limiter.hit("a", 2, 60)
    assert 59 < wait <= 60
    assert limiter.hit("b", 2, 60) == 0.0  # khóa khác không bị ảnh hưởng
    now[0] += 61
    assert limiter.hit("a", 2, 60) == 0.0  # cửa sổ đã trượt qua


def test_limiter_sweeps_idle_keys():
    now = [0.0]
    limiter = SlidingWindowLimiter(clock=lambda: now[0], sweep_every=3)
    for i in range(3):
        limiter.hit(f"k{i}", 5, 10)
    now[0] = 100.0
    for i in range(3):
        limiter.hit("fresh", 5, 10)
    assert set(limiter._hits) == {"fresh"}


# ---------- rate limit qua HTTP ----------

def test_analyze_rate_limited_per_ip(tmp_path, fake_analyzer):
    client = TestClient(create_app(make_settings(tmp_path, rate_limit_analyze=3)))
    assert [client.post("/v1/analyze", json=TEXT).status_code for _ in range(3)] == [200, 200, 200]
    response = client.post("/v1/analyze", json=TEXT)
    assert_error(response, 429, "rate_limited")
    assert 1 <= int(response.headers["Retry-After"]) <= 60
    assert len(fake_analyzer.calls) == 3  # request bị chặn không tới analyzer (không tốn tiền LLM)


def test_invalid_requests_also_count(tmp_path):
    client = TestClient(create_app(make_settings(tmp_path, rate_limit_analyze=2)))
    assert [client.post("/v1/analyze", json={}).status_code for _ in range(3)] == [422, 422, 429]


def test_buckets_are_independent_and_health_is_exempt(tmp_path, fake_analyzer):
    client = TestClient(create_app(make_settings(tmp_path, rate_limit_analyze=1, rate_limit_reports=1,
                                                 rate_limit_default=1)))
    assert client.post("/v1/analyze", json=TEXT).status_code == 200
    assert client.post("/v1/analyze", json=TEXT).status_code == 429
    assert client.post("/v1/reports", json={"text": "abc"}).status_code == 201
    assert client.post("/v1/reports", json={"text": "abc"}).status_code == 429
    assert client.post("/v1/qr/parse", json={"payload": "000201010211"}).status_code == 200
    assert client.post("/v1/qr/parse", json={"payload": "000201010211"}).status_code == 429
    assert all(client.get("/health").status_code == 200 for _ in range(20))


def test_forwarded_header_ignored_unless_proxy_trusted(tmp_path):
    client = TestClient(create_app(make_settings(tmp_path, rate_limit_analyze=1)))
    assert client.post("/v1/analyze", json={}, headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 422
    # đổi X-Forwarded-For không né được giới hạn
    assert client.post("/v1/analyze", json={}, headers={"X-Forwarded-For": "2.2.2.2"}).status_code == 429


def test_each_client_ip_has_its_own_limit_behind_trusted_proxy(tmp_path):
    client = TestClient(create_app(make_settings(tmp_path, rate_limit_analyze=1, trusted_proxy_count=1)))

    def post(ip, spoof=""):
        return client.post("/v1/analyze", json={}, headers={"X-Forwarded-For": f"{spoof}{ip}"}).status_code

    assert post("1.1.1.1") == 422
    assert post("1.1.1.1") == 429
    assert post("2.2.2.2") == 422  # IP khác → hạn mức riêng
    assert post("1.1.1.1", spoof="9.9.9.9, ") == 429  # IP giả đặt bên trái không có tác dụng


# ---------- CORS ----------

def test_cors_preflight_allows_localhost_3000(client):
    response = client.options("/v1/analyze", headers={"Origin": ORIGIN, "Access-Control-Request-Method": "POST",
                                                      "Access-Control-Request-Headers": "content-type"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert "POST" in response.headers["access-control-allow-methods"]


def test_cors_headers_on_normal_and_error_responses(client, fake_analyzer):
    ok = client.post("/v1/analyze", json=TEXT, headers={"Origin": ORIGIN})
    err = client.post("/v1/analyze", json={}, headers={"Origin": ORIGIN})
    assert ok.headers["access-control-allow-origin"] == ORIGIN
    assert err.status_code == 422 and err.headers["access-control-allow-origin"] == ORIGIN


def test_cors_headers_on_429(tmp_path):
    client = TestClient(create_app(make_settings(tmp_path, rate_limit_analyze=1)))
    for _ in range(2):
        response = client.post("/v1/analyze", json={}, headers={"Origin": ORIGIN})
    assert response.status_code == 429 and response.headers["access-control-allow-origin"] == ORIGIN
    assert "retry-after" in response.headers["access-control-expose-headers"].lower()


def test_cors_rejects_other_origins(client):
    response = client.options("/v1/analyze", headers={"Origin": "https://evil.example",
                                                      "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in response.headers
    assert response.status_code == 400
    get = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in get.headers


def test_cors_origins_come_from_settings(tmp_path):
    client = TestClient(create_app(make_settings(tmp_path, allowed_origins=("https://app.example.vn",))))
    assert client.get("/health", headers={"Origin": "https://app.example.vn"}).headers[
        "access-control-allow-origin"] == "https://app.example.vn"
    assert "access-control-allow-origin" not in client.get("/health", headers={"Origin": ORIGIN}).headers


# ---------- giới hạn body ----------

def test_content_length_over_limit_is_413_before_parsing(tmp_path, fake_analyzer):
    client = TestClient(create_app(make_settings(tmp_path, max_body_bytes=1000)))
    response = client.post("/v1/analyze", json={"text": "a" * 2000})
    assert_error(response, 413, "body_too_large")
    assert fake_analyzer.calls == []


def _post_chunked(app, chunks):
    """Gọi thẳng ASGI, không có Content-Length (giống chunked transfer) để thử đếm byte thực."""
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST",
             "path": "/v1/analyze", "raw_path": b"/v1/analyze", "query_string": b"", "scheme": "http",
             "headers": [(b"content-type", b"application/json")], "client": ("9.9.9.9", 1), "server": ("t", 80)}
    pending = list(chunks)
    sent = []

    async def receive():
        if pending:
            body = pending.pop(0)
            return {"type": "http.request", "body": body, "more_body": bool(pending)}
        return {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)

    asyncio.run(app(scope, receive, send))
    start = next(m for m in sent if m["type"] == "http.response.start")
    return start["status"], b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")


def test_chunked_body_over_limit_is_413_without_content_length(tmp_path, fake_analyzer):
    app = create_app(make_settings(tmp_path, max_body_bytes=1000))
    status, body = _post_chunked(app, [b'{"text": "' + b"a" * 600, b"b" * 600 + b'"}'])
    assert status == 413 and b"body_too_large" in body
    assert fake_analyzer.calls == []


def test_chunked_body_under_limit_still_works(tmp_path, fake_analyzer):
    app = create_app(make_settings(tmp_path, max_body_bytes=1000))
    status, _ = _post_chunked(app, [b'{"text": "Chuy', b'en tien gap"}'])
    assert status == 200
