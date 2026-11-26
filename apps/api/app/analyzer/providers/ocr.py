import base64
import binascii
import csv
import io
import subprocess

from PIL import Image, ImageOps

from ...media import media_slot, read_media
from ..contract import AnalyzerError

MAX_IMAGE_BYTES = 5 * 1024 * 1024


def decode_image(encoded, mime):
    if mime not in {"image/png", "image/jpeg"}:
        raise AnalyzerError(415, "Chỉ hỗ trợ ảnh PNG hoặc JPEG.")
    if len(encoded) > 4 * ((MAX_IMAGE_BYTES + 2) // 3):
        raise AnalyzerError(413, "Ảnh vượt quá 5 MB.")
    try:
        data = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise AnalyzerError(422, "Dữ liệu ảnh không hợp lệ.") from exc
    if len(data) > MAX_IMAGE_BYTES:
        raise AnalyzerError(413, "Ảnh vượt quá 5 MB.")
    return open_image(data, mime)


def open_image(data, mime):
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format != {"image/png": "PNG", "image/jpeg": "JPEG"}[mime]:
                raise AnalyzerError(415, "Định dạng ảnh không khớp nội dung.")
            if image.width * image.height > 16_000_000:
                raise AnalyzerError(413, "Kích thước ảnh quá lớn.")
            image.load()
            return ImageOps.exif_transpose(image).convert("RGB")
    except Image.DecompressionBombError as exc:
        raise AnalyzerError(413, "Kích thước ảnh quá lớn.") from exc
    except (OSError, ValueError, SyntaxError) as exc:
        raise AnalyzerError(422, "Ảnh hỏng hoặc không đọc được.") from exc


def image_for(request):
    if request.image_base64 is None:
        if request.image_mime is not None:
            raise AnalyzerError(422, "Thiếu dữ liệu ảnh.")
        return None
    return decode_image(request.image_base64, request.image_mime)


def read_image(image, settings):
    with media_slot():
        return recognize(image, settings)


def recognize(image, settings):
    return _recognize(image, settings, boxes=False)[0]


def _recognize(image, settings, *, boxes):
    image = image.copy()
    image.thumbnail((2000, 2000))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    try:
        if settings.ocr_command:
            result = subprocess.run(
                [settings.ocr_command, "stdin", "stdout", "-l", settings.ocr_languages, "--psm", "11"]
                + (["tsv"] if boxes else []),
                input=buffer.getvalue(), capture_output=True, check=True, timeout=5,
            )
            text = result.stdout.decode("utf-8", errors="replace")
        else:
            text = read_media("ocr-tsv" if boxes else "ocr", buffer.getvalue(), settings, timeout=6)
    except (OSError, subprocess.SubprocessError) as exc:
        raise AnalyzerError(503, "Bộ đọc chữ đang gián đoạn. Bạn có thể thử dán nội dung tin nhắn.") from exc
    if not boxes:
        if not any(char.isalnum() for char in text):
            raise AnalyzerError(422, "Chưa đọc được chữ trong ảnh. Hãy dùng ảnh rõ hơn hoặc dán nội dung.")
        return text.strip()[:12000], []
    words, regions = [], []
    for row in csv.DictReader(io.StringIO(text), delimiter="\t"):
        word = (row.get("text") or "").strip()
        if row.get("level") != "5" or not word:
            continue
        try:
            left, top, width, height = (int(row[key]) for key in ("left", "top", "width", "height"))
        except (KeyError, TypeError, ValueError):
            continue
        if not (0 <= left < left + width <= image.width and 0 <= top < top + height <= image.height):
            continue
        words.append(word)
        regions.append([round(value, 4) for value in (left / image.width, top / image.height,
                                                       width / image.width, height / image.height)])
        if len(regions) == 250:
            break
    return " ".join(words)[:12000], regions


def read_document(image, settings):
    with media_slot():
        return _recognize(image, settings, boxes=True)
