"""Middleware ASGI thuần: giới hạn dung lượng body và rate limit theo IP."""
import math
import threading
import time
from collections import deque
from collections.abc import Callable

from app.core.config import Settings
from app.core.errors import ApiError, error_response

TOO_LARGE_MESSAGE = "Dữ liệu gửi lên quá lớn. Ảnh tối đa 5 MB — hãy nén hoặc cắt nhỏ ảnh rồi thử lại."
RATE_LIMITED_MESSAGE = "Bạn gửi quá nhanh. Vui lòng đợi một chút rồi thử lại."


def _header(scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key == name:
            return value.decode("latin-1")
    return None


class BodySizeLimitMiddleware:
    """Chặn body quá lớn: theo Content-Length trước, rồi đếm byte thực khi đọc (chống chunked)."""

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = _header(scope, b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > self.max_bytes:
            response = error_response(413, "body_too_large", TOO_LARGE_MESSAGE)
            await response(scope, receive, send)
            return

        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise ApiError(413, "body_too_large", TOO_LARGE_MESSAGE)
            return message

        await self.app(scope, limited_receive, send)


class SlidingWindowLimiter:
    """Cửa sổ trượt trong bộ nhớ. Đủ cho 1 instance (runbook giữ 1 instance); nhiều instance cần Redis."""

    def __init__(self, clock: Callable[[], float] = time.monotonic, sweep_every: int = 1024):
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._sweep_every = sweep_every
        self._calls = 0

    def hit(self, key: str, limit: int, window_s: float) -> float:
        """Ghi 1 request. Trả 0.0 nếu được phép, ngược lại trả số giây phải đợi."""
        now = self._clock()
        cutoff = now - window_s
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= limit:
                return max(hits[0] + window_s - now, 0.001)
            hits.append(now)
            self._calls += 1
            if self._calls % self._sweep_every == 0:
                self._sweep(cutoff)
            return 0.0

    def _sweep(self, cutoff: float) -> None:
        for key in [k for k, q in self._hits.items() if not q or q[-1] <= cutoff]:
            del self._hits[key]


def client_ip(scope, trusted_proxy_count: int) -> str:
    """IP client. Chỉ tin X-Forwarded-For khi khai báo số proxy tin cậy; lấy phần tử thứ N từ phải sang."""
    peer = (scope.get("client") or ("unknown", 0))[0]
    if trusted_proxy_count > 0:
        forwarded = _header(scope, b"x-forwarded-for")
        if forwarded:
            hops = [h.strip() for h in forwarded.split(",") if h.strip()]
            if len(hops) >= trusted_proxy_count:
                return hops[-trusted_proxy_count]
    return peer


def bucket_for(method: str, path: str) -> str | None:
    """Nhóm giới hạn của request; None = không giới hạn (health, preflight CORS, tài liệu)."""
    if method == "OPTIONS" or path == "/health":
        return None
    if path == "/v1/analyze":
        return "analyze"
    if path == "/v1/reports":
        return "reports"
    if path.startswith("/v1/"):
        return "default"
    return None


class RateLimitMiddleware:
    def __init__(self, app, settings: Settings, limiter: SlidingWindowLimiter):
        self.app = app
        self.settings = settings
        self.limiter = limiter
        self._limits = {"analyze": settings.rate_limit_analyze,
                        "reports": settings.rate_limit_reports,
                        "default": settings.rate_limit_default}

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        bucket = bucket_for(scope["method"], scope["path"])
        if bucket is not None:
            # Hôm nay khóa theo IP; khi có đăng nhập thêm khóa theo tài khoản + nới hạn mức cho tài khoản BGK.
            key = f"{bucket}:ip:{client_ip(scope, self.settings.trusted_proxy_count)}"
            retry_after = self.limiter.hit(key, self._limits[bucket], self.settings.rate_limit_window_s)
            if retry_after > 0:
                response = error_response(429, "rate_limited", RATE_LIMITED_MESSAGE,
                                          headers={"Retry-After": str(math.ceil(retry_after))})
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
