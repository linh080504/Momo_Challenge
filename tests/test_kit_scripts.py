"""Kiểm tra các script trong bộ kit. Chạy: python3 -m pytest tests/ -q  (hoặc python3 tests/test_kit_scripts.py)"""
import base64
import contextlib
import http.server
import io
import json
import os
import pathlib
import sys
import tempfile
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parents[1] / ".claude" / "skills"
for sub in ("vietqr/scripts", "pii-guard/scripts", "evidence-tools/scripts", "eval-harness/scripts"):
    sys.path.insert(0, str(ROOT / sub))

import domain_check  # noqa: E402
import pii_mask  # noqa: E402
import run_eval  # noqa: E402
import vietqr  # noqa: E402


def test_crc_check_value():
    assert vietqr.crc16_ccitt_false("123456789") == "29B1"


def test_vietqr_roundtrip():
    payload = vietqr.build("970436", "0123456789", 50000, "TKC 123")
    qr = vietqr.parse(payload)
    assert qr.valid_crc and qr.is_napas
    assert (qr.bank_bin, qr.account, qr.amount, qr.note) == ("970436", "0123456789", "50000", "TKC 123")
    assert qr.initiation == "dynamic"


def test_vietqr_tampered_crc():
    payload = vietqr.build("970436", "0123456789", 50000)
    tampered = payload.replace("0123456789", "0987654321")
    assert not vietqr.parse(tampered).valid_crc


def test_pii_keeps_amounts_and_masks_ids():
    r = pii_mask.mask_text("Chuyển 5.000.000đ vào STK 0123456789, gọi 0912 345 678, OTP: 482913")
    assert "5.000.000đ" in r["masked"]
    assert "0123456789" not in r["masked"] and "[ACCOUNT_1]" in r["masked"]
    assert "[PHONE_1]" in r["masked"] and "[OTP_1]" in r["masked"]


def test_pii_same_value_same_token():
    r = pii_mask.mask_text("gọi 0912345678 hoặc +84912345678")
    assert r["masked"].count("[PHONE_1]") == 2


def test_domain_official_vs_fake():
    assert domain_check.check("https://ebank.vietcombank.com.vn")["level"] == "low"
    assert domain_check.check("https://vietcombank-xacminh.top/login")["level"] == "high"
    assert domain_check.check("http://vietcombank.com.vn.secure-id.xyz")["level"] == "high"
    assert domain_check.check("http://192.168.1.10/login")["level"] == "high"


def test_baseline_rules():
    assert run_eval.baseline_predict("Đọc giúp em mã OTP")["risk_level"] == "high"
    assert run_eval.baseline_predict("Tối nay ăn cơm nhé")["risk_level"] == "low"


# ---- run_eval: mẫu ảnh -------------------------------------------------------------------------------------------

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake-png-body"
JPG_BYTES = b"\xff\xd8\xff\xe0" + b"fake-jpg-body"


def _raises(exc_type, fn):
    try:
        fn()
    except exc_type as exc:
        return exc
    raise AssertionError(f"không ném {exc_type.__name__}")


def _serve(image_delay=0.0):
    """Máy chủ giả cho /v1/analyze: ghi lại thân POST, luôn trả risk_level high."""
    received = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            received.append(body)
            if "image_base64" in body:
                time.sleep(image_delay)
            data = json.dumps({"risk_level": "high", "scenario_group": "G5"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, received


def _run(argv):
    """Chạy run_eval.main, trả (exit_code, summary đọc từ file báo cáo có dấu thời gian)."""
    out_dir = pathlib.Path(argv[argv.index("--out") + 1])
    old_no_proxy = os.environ.get("NO_PROXY")
    os.environ["NO_PROXY"] = "127.0.0.1"  # tránh proxy hệ thống chặn kết nối vào máy chủ giả
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            code = run_eval.main(argv)
    finally:
        if old_no_proxy is None:
            os.environ.pop("NO_PROXY", None)
        else:
            os.environ["NO_PROXY"] = old_no_proxy
    report = next(p for p in out_dir.glob("*.json") if p.name not in {"latest.json", "last_run.json"})
    parsed = json.loads(report.read_text(encoding="utf-8"))
    assert json.loads((out_dir / "last_run.json").read_text(encoding="utf-8")) == parsed["summary"]
    return code, parsed


def _dataset(directory, rows):
    path = pathlib.Path(directory) / "data.jsonl"
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    return str(path)


def test_baseline_image_is_unreadable_even_with_keyword_text():
    with_image = {"text": "Đọc giúp em mã OTP", "image": "eval/images/x.png"}
    assert run_eval.baseline_predict_row(with_image)["risk_level"] == "low"
    assert run_eval.baseline_predict_row({"text": "Đọc giúp em mã OTP"})["risk_level"] == "high"


def test_build_payload_text_sample_keeps_old_shape():
    assert run_eval.build_payload({"text": "abc", "label": "legit"}) == {"text": "abc"}


def test_build_payload_image_mime_follows_content_not_extension():
    with tempfile.TemporaryDirectory() as d:
        png = pathlib.Path(d, "looks-like.jpg")  # đuôi sai cố ý
        png.write_bytes(PNG_BYTES)
        jpg = pathlib.Path(d, "looks-like.png")
        jpg.write_bytes(JPG_BYTES)
        p1 = run_eval.build_payload({"text": "kèm chữ", "image": str(png)})
        p2 = run_eval.build_payload({"image": str(jpg)})  # không có "text"
    assert p1["image_mime"] == "image/png" and p1["text"] == "kèm chữ"
    assert base64.b64decode(p1["image_base64"]) == PNG_BYTES
    assert p2["image_mime"] == "image/jpeg" and p2["text"] == ""
    assert base64.b64decode(p2["image_base64"]) == JPG_BYTES
    assert set(p1) == set(p2) == {"text", "image_base64", "image_mime"}


def test_build_payload_image_rejects_gif_oversize_and_missing():
    limit = run_eval.MAX_IMAGE_BYTES
    assert limit == 5 * 1024 * 1024
    with tempfile.TemporaryDirectory() as d:
        gif = pathlib.Path(d, "a.png")
        gif.write_bytes(b"GIF89a" + b"x" * 10)
        exact = pathlib.Path(d, "exact.png")
        exact.write_bytes(PNG_BYTES + b"\0" * (limit - len(PNG_BYTES)))
        over = pathlib.Path(d, "over.png")
        over.write_bytes(PNG_BYTES + b"\0" * (limit - len(PNG_BYTES) + 1))
        _raises(ValueError, lambda: run_eval.build_payload({"image": str(gif)}))
        _raises(ValueError, lambda: run_eval.build_payload({"image": str(over)}))
        _raises(OSError, lambda: run_eval.build_payload({"image": str(pathlib.Path(d, "none.png"))}))
        assert run_eval.build_payload({"image": str(exact)})["image_mime"] == "image/png"  # đúng 5 MB vẫn nhận


def test_run_eval_sends_image_payload_and_reports_p95_by_type():
    server, received = _serve()
    try:
        with tempfile.TemporaryDirectory() as d:
            png, jpg = pathlib.Path(d, "a.png"), pathlib.Path(d, "b.jpg")
            png.write_bytes(PNG_BYTES)
            jpg.write_bytes(JPG_BYTES)
            data = _dataset(d, [
                {"id": "t1", "text": "Đọc giúp em mã OTP", "label": "scam", "group": "G5"},
                {"id": "i1", "text": "", "label": "scam", "group": "G5", "image": str(png), "tags": ["image"]},
                {"id": "i2", "label": "scam", "group": "G5", "image": str(jpg), "tags": ["image"]},
            ])
            out = str(pathlib.Path(d, "out"))
            url = f"http://127.0.0.1:{server.server_port}/v1/analyze"
            code, report = _run(["--data", data, "--endpoint", url, "--tag", "t", "--out", out])
            latest_written = pathlib.Path(out, "latest.json").exists()
    finally:
        server.shutdown()
        server.server_close()
    summary = report["summary"]
    assert code == 0 and summary["passed"] and latest_written
    assert [r["input_type"] for r in report["results"]] == ["text", "image", "image"]
    assert (summary["n_text"], summary["n_image"], summary["errors"]) == (1, 2, 0)
    assert summary["p95_text"] is not None and summary["p95_image"] is not None
    assert received[0] == {"text": "Đọc giúp em mã OTP"}  # mẫu văn bản: thân JSON như cũ
    assert set(received[1]) == set(received[2]) == {"text", "image_base64", "image_mime"}
    assert (received[1]["text"], received[1]["image_mime"]) == ("", "image/png")
    assert (received[2]["text"], received[2]["image_mime"]) == ("", "image/jpeg")
    assert base64.b64decode(received[1]["image_base64"]) == PNG_BYTES
    assert base64.b64decode(received[2]["image_base64"]) == JPG_BYTES


def test_run_eval_sends_new_modalities_without_reference_labels(tmp_path):
    server, received = _serve()
    try:
        image = tmp_path / "receipt.png"
        image.write_bytes(PNG_BYTES)
        audio = tmp_path / "sample.wav"
        audio.write_bytes(b"synthetic-audio-fixture")
        rows = [
            {"url": "https://example.org/"},
            {"qr_payload": "https://example.org/"},
            {"audio": str(audio), "transcript": "benchmark reference"},
            {"image": str(image), "image_kind": "receipt", "transcript": "OCR reference"},
        ]
        data = _dataset(tmp_path, [{"id": str(i), "label": "scam", "group": "G5", "synthetic": True, **row}
                                   for i, row in enumerate(rows)])
        url = f"http://127.0.0.1:{server.server_port}/v1/analyze"
        _, report = _run(["--data", data, "--endpoint", url, "--out", str(tmp_path / "out")])
    finally:
        server.shutdown()
        server.server_close()
    summary = report["summary"]
    assert summary["synthetic_count"] == 4
    assert all(summary["by_input"][kind]["n"] == 1 and summary["by_input"][kind]["errors"] == 0
               for kind in ("url", "qr", "audio", "receipt"))
    assert received[0] == {"text": "", "url": "https://example.org/"}
    assert received[1] == {"text": "", "qr_payload": "https://example.org/"}
    assert base64.b64decode(received[2]["audio_base64"]) == audio.read_bytes()
    assert received[3]["image_kind"] == "receipt"
    assert all("transcript" not in payload and "label" not in payload for payload in received)


def test_run_eval_p95_gates_are_separate():
    server, _ = _serve(image_delay=0.15)
    try:
        with tempfile.TemporaryDirectory() as d:
            png = pathlib.Path(d, "a.png")
            png.write_bytes(PNG_BYTES)
            data = _dataset(d, [
                {"id": "t1", "text": "Đọc giúp em mã OTP", "label": "scam", "group": "G5"},
                {"id": "i1", "text": "", "label": "scam", "group": "G5", "image": str(png)},
            ])
            out = str(pathlib.Path(d, "out"))
            url = f"http://127.0.0.1:{server.server_port}/v1/analyze"
            code, report = _run(["--data", data, "--endpoint", url, "--out", out,
                                 "--max-p95-text", "6", "--max-p95-image", "0.05"])
    finally:
        server.shutdown()
        server.server_close()
    gates = report["summary"]["gates"]
    text_gate = [ok for name, ok in gates.items() if name.startswith("p95 văn bản")]
    image_gate = [ok for name, ok in gates.items() if name.startswith("p95 ảnh")]
    assert text_gate == [True] and image_gate == [False]
    assert code == 1 and not report["summary"]["passed"]
    assert report["summary"]["p95_image"] >= 0.15


def test_run_eval_unreadable_image_is_error_not_safe_and_not_in_latency():
    server, received = _serve()
    try:
        with tempfile.TemporaryDirectory() as d:
            data = _dataset(d, [{"id": "i1", "text": "", "label": "scam", "group": "G5",
                                 "image": str(pathlib.Path(d, "missing.png"))}])
            out = str(pathlib.Path(d, "out"))
            url = f"http://127.0.0.1:{server.server_port}/v1/analyze"
            code, report = _run(["--data", data, "--endpoint", url, "--out", out])
    finally:
        server.shutdown()
        server.server_close()
    summary = report["summary"]
    assert code == 1 and summary["errors"] == 1 and received == []  # chưa gọi API
    assert report["results"][0]["pred"] == "error" and not report["results"][0]["flagged"]
    assert summary["p95_image"] is None  # không có lần gọi nào để đo
    assert report["errors"][0]["id"] == "i1" and report["errors"][0]["input_type"] == "image"
    assert not any(name.startswith("p95 ảnh") for name in summary["gates"])


def test_run_eval_baseline_counts_image_samples_as_unreadable():
    with tempfile.TemporaryDirectory() as d:
        data = _dataset(d, [
            {"id": "t1", "text": "Đọc giúp em mã OTP", "label": "scam", "group": "G5"},
            {"id": "i1", "text": "Đọc giúp em mã OTP", "label": "scam", "group": "G5", "image": "eval/images/i1.png"},
        ])
        out = str(pathlib.Path(d, "out"))
        code, report = _run(["--data", data, "--baseline", "--out", out])
    summary = report["summary"]
    by_id = {r["id"]: r for r in report["results"]}
    assert by_id["t1"]["pred"] == "high" and by_id["i1"]["pred"] == "low"
    assert summary["missed_scams"] == ["i1"] and summary["recall_scam"] == 0.5
    assert (summary["n_text"], summary["n_image"]) == (1, 1)
    assert code == 1  # recall 0.5 < 0.90


def test_run_eval_old_max_p95_flag_is_rejected():
    for flag in ("--max-p95", "--max-p95-all"):
        with contextlib.redirect_stderr(io.StringIO()):
            exc = _raises(SystemExit, lambda: run_eval.main(["--data", "x", "--baseline", flag, "8"]))
        assert exc.code == 2


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("OK", name)
