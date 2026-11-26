"""Trích thực thể từ văn bản + băm để lưu/tra cứu.

Khóa tra cứu là HMAC-SHA256 với khóa bí mật `ENTITY_HASH_KEY` (không phải SHA-256 trần): SĐT/STK có không gian
giá trị nhỏ, ai có DB mà không có khóa vẫn không dò ngược được bằng cách thử hết các số.
`EntityHasher.hash` là điểm DUY NHẤT định nghĩa khóa tra cứu — mọi nơi tra danh sách đen (kể cả analyzer/evidence)
phải dùng nó.

Hệ quả vận hành: ĐỔI KHÓA = mọi hash cũ mất tác dụng và không băm lại được (giá trị gốc không được lưu).
Chọn khóa một lần, giữ ở secret của nhà cung cấp, sao lưu riêng.

Lưu ở bảng `entities`: SĐT/STK/thẻ/email chỉ giữ hash + dạng đã che. Tên miền lưu đầy đủ (quyết định PM) — chỉ phần
host, bỏ đường dẫn/tham số vì chúng có thể chứa mã phiên hay định danh cá nhân.
"""
import hashlib
import hmac
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.privacy.mask import Masker, digits_only

MIN_KEY_CHARS = 32  # token_hex(16) trở lên; ngắn hơn thì HMAC không còn ý nghĩa chống dò ngược
ENTITY_TYPES = ("ACCOUNT", "PHONE", "URL", "EMAIL", "CARD", "AMOUNT", "BANK", "ORG")  # = enum trong analysis.schema.json
_MASK_KIND_TO_TYPE = {"PHONE": "PHONE", "ACCOUNT": "ACCOUNT", "CARD": "CARD", "EMAIL": "EMAIL"}  # OTP/ID: bỏ, không lưu
_URL = re.compile(r"(?i)\b(?:https?://|www\.)[^\s<>\"'()\[\]]+")


@dataclass(frozen=True)
class ExtractedEntity:
    type: str
    value_hash: str
    display: str


def normalize(entity_type: str, value: str) -> str:
    value = value.strip()
    if entity_type == "PHONE":
        return "0" + digits_only(value)[-9:]
    if entity_type in ("ACCOUNT", "CARD"):
        return digits_only(value)
    if entity_type == "URL":
        return _host_of(value) or value.lower()
    return value.lower()


def _host_of(url: str) -> str | None:
    candidate = url if re.match(r"(?i)^https?://", url) else f"http://{url}"
    try:
        host = urlsplit(candidate).hostname
    except ValueError:
        return None
    if not host:
        return None
    host = host.lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def display_value(entity_type: str, value: str) -> str:
    """Dạng hiển thị cho vận hành. SĐT/STK/thẻ/email bị che (0912****78); tên miền giữ nguyên."""
    v = normalize(entity_type, value)
    if entity_type == "URL":
        return v
    if entity_type == "EMAIL":
        local, _, domain = v.partition("@")
        return f"{local[:1]}***@{domain}"
    if len(v) >= 8:
        return f"{v[:4]}{'*' * (len(v) - 6)}{v[-2:]}"
    return "*" * len(v)


class EntityHasher:
    def __init__(self, key: str):
        if not key or len(key) < MIN_KEY_CHARS:
            raise ValueError(
                f"ENTITY_HASH_KEY chưa đặt hoặc quá ngắn (cần ít nhất {MIN_KEY_CHARS} ký tự). "
                'Tạo khóa: py -3 -c "import secrets; print(secrets.token_hex(32))" rồi dán vào .env.')
        self._key = key.encode("utf-8")

    def hash(self, entity_type: str, value: str) -> str:
        """HMAC-SHA256 (64 ký tự hex) của `loại:giá trị chuẩn hóa`. Có `loại` trong thông điệp để hai loại
        khác nhau không bao giờ trùng hash. Dùng đủ 64 ký tự: hash trùng ở danh sách đen = người vô can bị gắn nhãn."""
        message = f"{entity_type}:{normalize(entity_type, value)}".encode("utf-8")
        return hmac.new(self._key, message, hashlib.sha256).hexdigest()

    def extract(self, text: str, masker: Masker) -> list[ExtractedEntity]:
        """`masker` phải là Masker đã `mask(text)`. SĐT/STK/thẻ/email lấy từ mapping; URL lấy từ chính văn bản."""
        found: dict[tuple[str, str], ExtractedEntity] = {}

        def add(entity_type: str, value: str) -> None:
            h = self.hash(entity_type, value)
            found.setdefault((entity_type, h), ExtractedEntity(entity_type, h, display_value(entity_type, value)))

        for token, value in masker.mapping.items():
            entity_type = _MASK_KIND_TO_TYPE.get(token.strip("[]").rsplit("_", 1)[0])
            if entity_type:
                add(entity_type, value)
        for match in _URL.finditer(text):
            host = _host_of(match.group(0).rstrip(".,;:!?"))
            if host:
                add("URL", host)
        return list(found.values())
