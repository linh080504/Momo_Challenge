import io
import re
from statistics import median

from PIL import Image, ImageChops, ImageStat


def jpeg_residual_regions(image):
    sample = image.copy()
    sample.thumbnail((640, 640))
    if min(sample.size) < 96:
        return []
    encoded = io.BytesIO()
    sample.save(encoded, "JPEG", quality=90)
    with Image.open(encoded) as recompressed:
        difference = ImageChops.difference(sample, recompressed.convert("RGB"))
    cells = []
    for y in range(8):
        for x in range(8):
            region = (sample.width * x // 8, sample.height * y // 8,
                      sample.width * (x + 1) // 8, sample.height * (y + 1) // 8)
            mean = sum(ImageStat.Stat(difference.crop(region)).mean) / 3
            cells.append((mean, [x / 8, y / 8, 1 / 8, 1 / 8]))
    baseline = median(mean for mean, _ in cells)
    return [box for mean, box in sorted(cells, reverse=True)[:8] if mean >= max(12, baseline * 3)]


def inspect_document(image, mime, text, boxes):
    areas = jpeg_residual_regions(image) if mime == "image/jpeg" else []
    trace = "Ảnh có thông tin EXIF." if image.getexif() else "Ảnh thiếu thông tin EXIF."
    signals = [{"category": "physical", "finding": trace}]
    if areas:
        signals.append({"category": "physical", "finding": "Một số vùng có sai khác nén cao khi mã hóa lại JPEG."})
    if boxes:
        signals.append({"category": "visual", "finding": f"Xác định vị trí {len(boxes)} vùng chữ để đối chiếu bố cục."})
    if re.search(r"(?:thành công|successful)", text, re.I):
        signals.append({"category": "semantic", "finding": "OCR đọc được chữ thể hiện giao dịch thành công trên ảnh."})
    if re.search(r"\d[\d., ]*\s*(?:VND|VNĐ|₫)", text, re.I):
        signals.append({"category": "semantic", "finding": "OCR đọc được một giá trị tiền VND trên ảnh."})
    return {
        "ocr_boxes": boxes,
        "recompression_regions": areas,
        "signals": signals,
        "transaction_status": "unverified",
        "notice": "Ảnh biên lai cần đối chiếu với số dư và lịch sử giao dịch tại ngân hàng. Vùng sai khác nén có thể do ứng dụng nhắn tin nén ảnh.",
    }
