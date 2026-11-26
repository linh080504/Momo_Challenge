"""Convert a few synthetic text samples to controlled OCR fixtures."""

import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "generated"
IMAGE_IDS = {"s001", "s006", "s010", "l001", "l006"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sample = ROOT / "eval" / "dataset.example.jsonl"
    rows = [json.loads(line) for line in sample.read_text(encoding="utf-8").splitlines() if line]
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 35)
    except OSError:
        font = ImageFont.truetype("arial.ttf", 35)
    images = []
    for row in rows:
        if row["id"] not in IMAGE_IDS:
            continue
        image_id = "image-" + row["id"]
        text = textwrap.fill(row["text"], width=48, break_long_words=False, break_on_hyphens=False)
        image = Image.new("RGB", (1280, 80 + 54 * (text.count("\n") + 1)), "#ffffff")
        draw = ImageDraw.Draw(image)
        draw.multiline_text((42, 30), text, font=font, fill="#151515", spacing=16)
        path = OUT / (image_id + ".png")
        image.save(path)
        images.append({
            **row, "id": image_id, "text": "", "tags": row["tags"] + ["image"],
            "image": path.relative_to(ROOT).as_posix(), "source": "synthetic-rendered",
        })
    with (OUT / "dataset.smoke.jsonl").open("w", encoding="utf-8") as output:
        for row in rows + images:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Prepared {len(rows)} text and {len(images)} synthetic image fixtures.")


if __name__ == "__main__":
    main()
