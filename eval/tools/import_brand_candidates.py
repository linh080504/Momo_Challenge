"""Submit a bounded batch exported by an approved certificate or threat feed."""

import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import httpx


def addresses_from(path, certificate_export):
    with path.open("rb") as source:
        data = source.read(1_000_001)
    if len(data) > 1_000_000:
        raise ValueError("Tệp vượt quá 1 MB. Hãy chia lô.")
    if certificate_export:
        rows = json.loads(data)
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError("Tệp chứng chỉ cần là một mảng bản ghi.")
        lines = (name for row in rows if isinstance(row.get("name_value"), str) for name in row["name_value"].splitlines())
    else:
        lines = data.decode("utf-8-sig").splitlines()
    addresses = list(dict.fromkeys(line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")))
    if not addresses or len(addresses) > 100:
        raise ValueError("Mỗi lô cần từ 1 đến 100 địa chỉ khác nhau.")
    return addresses


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--source", choices=("CT_LOGS", "CSKH_REPORT", "QR_GATEWAY", "THREAT_INTEL", "QUICK_CHECK"), required=True)
    parser.add_argument("--certificate-export", action="store_true", help="Read newline-separated SANs from JSON name_value fields.")
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    target = urlsplit(args.api)
    if target.username or target.password or target.query or target.fragment or target.path not in ("", "/") or not target.hostname:
        parser.error("Địa chỉ API chỉ gồm giao thức, tên miền và cổng.")
    if target.scheme != "https" and not (target.scheme == "http" and target.hostname in {"localhost", "127.0.0.1", "::1"}):
        parser.error("Chỉ gửi mã phiên qua HTTPS hoặc tới máy local.")
    token = os.environ.get("PAYPAUSE_OPS_TOKEN")
    if not token:
        parser.error("Đặt PAYPAUSE_OPS_TOKEN bằng mã phiên của tài khoản vận hành.")
    if args.certificate_export and args.source != "CT_LOGS":
        parser.error("--certificate-export dùng với nguồn CT_LOGS.")
    try:
        addresses = addresses_from(args.input, args.certificate_export)
        response = httpx.post(args.api.rstrip("/") + "/v1/ops/brand-cases/intake",
                              headers={"Authorization": "Bearer " + token},
                              json={"source": args.source, "addresses": addresses}, timeout=15)
        response.raise_for_status()
        print(json.dumps(response.json(), ensure_ascii=False))
    except (ValueError, OSError) as exc:
        parser.exit(1, str(exc) + "\n")
    except httpx.HTTPStatusError as exc:
        parser.exit(1, f"API trả HTTP {exc.response.status_code}.\n")
    except httpx.HTTPError:
        parser.exit(1, "Không kết nối được API PayPause.\n")


if __name__ == "__main__":
    main()
