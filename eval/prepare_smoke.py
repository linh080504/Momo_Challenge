"""Convert a few synthetic text samples to controlled OCR fixtures."""

import argparse
import hashlib
import json
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "generated"
IMAGE_IDS = {"s001", "s006", "s010", "l001", "l006"}
sys.path.insert(0, str(ROOT / "apps" / "api"))
from app.kit import vietqr  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic-audio", type=Path, help="A synthetic WAV fixture for the technical smoke suite")
    args = parser.parse_args()
    if args.synthetic_audio is not None and not args.synthetic_audio.is_file():
        parser.error("Synthetic audio fixture does not exist.")
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

    receipt = OUT / "receipt.smoke.png"
    image = Image.new("RGB", (850, 230), "white")
    ImageDraw.Draw(image).multiline_text((32, 28), "Giao dịch thành công\nSố tiền: 125.000 VND",
                                        font=font, fill="black", spacing=16)
    image.save(receipt)
    extra = [
        {"id": "url-smoke-legit", "url": "https://momo.vn/", "label": "legit"},
        {"id": "url-smoke-risk", "url": "https://momo-kiemtra.example/", "label": "scam", "group": "G5"},
        {"id": "qr-smoke-payment", "qr_payload": vietqr.build("970436", "0000012345", 50000), "label": "legit"},
        {"id": "qr-smoke-link", "qr_payload": "https://momo-kiemtra.example/", "label": "scam", "group": "G5"},
        {"id": "receipt-smoke", "image_kind": "receipt", "image": receipt.relative_to(ROOT).as_posix(), "label": "legit"},
    ]
    if args.synthetic_audio is not None:
        extra.append({"id": "audio-smoke", "audio": args.synthetic_audio.as_posix(), "label": "legit"})
    path = OUT / "dataset.multimodal-smoke.jsonl"
    with path.open("w", encoding="utf-8") as output:
        for row in rows + images:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
        for row in extra:
            output.write(json.dumps({"synthetic": True, "source": "synthetic-smoke", **row}, ensure_ascii=False) + "\n")
    manifest = {"version": "multimodal-smoke-v1", "purpose": "technical-smoke", "n": len(rows + images + extra),
                "synthetic_count": len(rows + images + extra), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    (OUT / "multimodal-smoke.manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
