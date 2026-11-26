#!/usr/bin/env python3
"""Che thông tin cá nhân trên ảnh bằng Ô ĐEN (không làm mờ) rồi lưu bản sạch vào eval/images/.

- `boxes`: danh sách (x0, y0, x1, y1) theo tọa độ ẢNH GỐC. Tô đen đặc, không trong suốt.
- `crop`: (x0, y0, x1, y1) theo tọa độ ảnh gốc, cắt SAU khi tô đen (bỏ vùng thừa như khuôn mặt, tay).
- Lưu lại từ điểm ảnh nên mất toàn bộ EXIF/metadata. Ảnh gốc để NGOÀI repo.
- Ảnh đầu ra tối đa 5 MB (giới hạn của analyzer); tự giảm kích thước nếu vượt.
"""
from __future__ import annotations

import pathlib

from PIL import Image, ImageDraw

MAX_BYTES = 5 * 1024 * 1024


def redact(src: str, dst: str, boxes=(), crop=None, max_side: int = 2000) -> dict:
    im = Image.open(src).convert("RGB")
    draw = ImageDraw.Draw(im)
    for (x0, y0, x1, y1) in boxes:
        draw.rectangle((x0, y0, x1, y1), fill=(0, 0, 0))
    if crop:
        im = im.crop(crop)
    if max(im.size) > max_side:
        ratio = max_side / max(im.size)
        im = im.resize((round(im.width * ratio), round(im.height * ratio)), Image.LANCZOS)
    out = pathlib.Path(dst)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() in (".jpg", ".jpeg"):
        quality = 90
        while True:
            im.save(out, format="JPEG", quality=quality)
            if out.stat().st_size <= MAX_BYTES or quality <= 50:
                break
            quality -= 10
    else:
        im.save(out, format="PNG", optimize=True)
    size = out.stat().st_size
    if size > MAX_BYTES:
        raise ValueError(f"{dst}: {size} byte > 5 MB sau khi nén")
    return {"path": str(out), "size": im.size, "bytes": size, "boxes": len(boxes)}
