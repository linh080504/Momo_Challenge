"""Compare local OCR engines on images with QA transcripts."""

import argparse
import json
import math
import re
import statistics
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENGINES = ("tesseract", "pp-ocrv5", "pp-ocrv6-small")


def load_engine(name):
    if name == "tesseract":
        from app.analyzer.providers.ocr import recognize
        from app.config import Settings

        settings = Settings(_env_file=None, ocr_command="tesseract", ocr_languages="vie+eng")
        return lambda image: recognize(image, settings)

    import numpy as np
    from paddleocr import PaddleOCR

    detection, recognition = (("PP-OCRv5_mobile_det", "latin_PP-OCRv5_mobile_rec") if name == "pp-ocrv5" else
                              ("PP-OCRv6_small_det", "PP-OCRv6_small_rec"))
    ocr = PaddleOCR(text_detection_model_name=detection, text_recognition_model_name=recognition,
                    device="cpu", cpu_threads=2, enable_mkldnn=False,
                    text_det_limit_side_len=1280, text_det_limit_type="max",
                    use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False)

    def read(image):
        # Paddle uses BGR for array inputs. Keep line breaks in the recognized text.
        image.thumbnail((2000, 2000))
        result = ocr.predict(np.asarray(image)[:, :, ::-1].copy())
        return "\n".join(line for page in result for line in page["rec_texts"])

    return read


def words(text):
    return Counter(re.findall(r"\w+", unicodedata.normalize("NFC", text).casefold()))


def measure(ocr, rows):
    from app.analyzer.agents.analyze import Analyzer
    from app.analyzer.contract import AnalyzerError
    from app.analyzer.providers.ocr import open_image
    from app.analyzer.rules import evaluate_text
    from app.analyzer.signals.rules import match_rules
    from app.auth.security import Limits, Signer
    from app.config import Settings
    from app.evidence.safe_browsing import SafeBrowsing
    from app.privacy.entities import extract
    from app.schemas.requests import AnalyzeIn

    signer = Signer("local-ocr-evaluation-example-secret")
    settings = Settings(_env_file=None, dashscope_api_key="",
                        rdap_lookups_per_hour=0, fraud_url_model_path="")
    analyzer = Analyzer(settings, SimpleNamespace(matches=lambda _keys: False), signer, Limits(), SafeBrowsing(""))

    def signals(text):
        _, _, domains = extract(text, None, signer)
        rules = {rule.scenario for rule, _ in match_rules(text)}
        team_rules = {signal.id for signal in evaluate_text(text).signals}
        suspicious = {host for host, detail in domains.items() if detail["level"] != "low"}
        return rules, team_rules, suspicious

    results = []
    for row in rows:
        path = ROOT / row["image"]
        data = path.read_bytes()
        mime = "image/png" if data.startswith(b"\x89PNG\r\n\x1a\n") else "image/jpeg"
        image = open_image(data, mime)
        start = time.perf_counter()
        try:
            observed = ocr(image)
        except AnalyzerError as error:
            if error.status != 422:
                raise
            observed = ""
        latency_ms = round((time.perf_counter() - start) * 1000)
        expected_words = words(row["transcript"])
        expected_rules, expected_team_rules, expected_domains = signals(row["transcript"])
        observed_rules, observed_team_rules, observed_domains = signals(observed)
        risk = "unreadable"
        if observed.strip():
            with patch("app.analyzer.agents.analyze.read_image", return_value=observed):
                events = analyzer.events(AnalyzeIn(text=row.get("text") or ""), image)
                risk = next(event["result"]["risk_level"] for event in events if "result" in event)
        results.append({
            "id": row["id"], "latency_ms": latency_ms, "risk": risk, "blank": not bool(observed.strip()),
            "reference_words": expected_words.total(), "preserved_words": (expected_words & words(observed)).total(),
            "reference_rules": len(expected_rules), "preserved_rules": len(expected_rules & observed_rules),
            "reference_team_rules": len(expected_team_rules),
            "preserved_team_rules": len(expected_team_rules & observed_team_rules),
            "reference_domains": len(expected_domains), "preserved_domains": len(expected_domains & observed_domains),
        })
    return results


def summarize(results):
    latencies = sorted(row["latency_ms"] for row in results)
    counts = {key: sum(row[key] for row in results) for key in results[0] if key not in {"id", "latency_ms", "risk"}}
    return {"images": len(results), "p50_ms": statistics.median(latencies),
            "p95_ms": latencies[math.ceil(0.95 * len(latencies)) - 1],
            "risk_counts": dict(Counter(row["risk"] for row in results)), **counts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    data = parser.add_mutually_exclusive_group(required=True)
    data.add_argument("--dataset", type=Path)
    data.add_argument("--preload", action="store_true", help="Tải trọng số trước mà không đọc ảnh")
    parser.add_argument("--engines", nargs="+", choices=DEFAULT_ENGINES, default=DEFAULT_ENGINES)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / "apps" / "api"))

    if args.preload:
        for engine in args.engines:
            load_engine(engine)
        return
    rows = [json.loads(line) for line in args.dataset.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    images = [row for row in rows if row.get("image") and row.get("transcript") and row.get("image_kind") != "receipt"]
    if not images or not args.output:
        parser.error("Cần ảnh có bản chép và đường dẫn --output")
    report = {}
    for engine in args.engines:
        results = measure(load_engine(engine), images)
        report[engine] = {"summary": summarize(results), "results": results}
        print(engine, json.dumps(report[engine]["summary"]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
