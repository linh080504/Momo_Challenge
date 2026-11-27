"""Rehearse five synthetic campaigns against the local application in a temporary database."""
import argparse
import json
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


def run(client):
    def request(method, path, status=200, **kwargs):
        response = client.request(method, path, **kwargs)
        if response.status_code != status:
            raise RuntimeError(f"{method} {path}: HTTP {response.status_code}, expected {status}")
        return response.json()

    def login(role):
        result = request("POST", "/v1/auth/login", json={"email": f"{role}@example.invalid", "password": "rehearsal-pass"})
        return {"Authorization": "Bearer " + result["token"]}

    ops, user = login("ops"), login("user")
    cases = [json.loads(row) for row in (ROOT / "eval/dataset.example.jsonl").read_text(encoding="utf-8").splitlines()]
    fixtures = {group: next(row for row in cases if row.get("group") == group and row.get("synthetic") is True)
                for group in ("G1", "G2", "G3", "G4", "G5")}
    campaigns = []
    for index, (group, case) in enumerate(fixtures.items(), start=1):
        text = f"{case['text']} Số liên hệ mô phỏng 090000000{index}."
        ids = set()
        for _ in range(8):
            result = request("POST", "/v1/analyze", json={"text": text})
            created = request("POST", "/v1/reports", 201, headers=user,
                              json={"analysis_id": result["analysis_id"], "consent": True})
            ids.add(created["campaign_id"])
        if len(ids) != 1:
            raise RuntimeError(f"{group}: expected 1 campaign, got {len(ids)}")
        campaigns.append((group, ids.pop()))
    review_ms = []
    for _, campaign in campaigns:
        start = time.perf_counter()
        path = f"/v1/ops/campaigns/{campaign}"
        detail = request("GET", path, headers=ops)
        samples = request("GET", path + "/samples", headers=ops)["samples"]
        if len(samples) != 8 or detail["report_count"] != len(samples):
            raise RuntimeError("Campaign report counts differ")
        for sample in samples:
            request("POST", f"{path}/samples/{sample['id']}/review", headers=ops, json={"label": "scam", "revision": 0})
        request("POST", path + "/decision", headers=ops,
                json={"decision": "approve", "revision": detail["revision"]})
        review_ms.append(round((time.perf_counter() - start) * 1000, 1))
    overview = request("GET", "/v1/ops/overview", headers=ops)
    exported = request("GET", "/v1/ops/feedback/samples", headers=ops)["samples"]
    if len(exported) != 40 or overview["approved"] != 5:
        raise RuntimeError("Counts for labels and approved campaigns differ")
    return {"purpose": "synthetic_api_rehearsal", "campaigns": 5, "reports": 40,
            "decisions": overview["decisions_24h"], "labeled": len(exported), "review_api_ms": review_ms}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="paypause-rehearsal-") as temp:
        sqlite = (Path(temp) / "ops.sqlite3").as_posix()
        settings = Settings(_env_file=None, database_url=f"sqlite:///{sqlite}",
                            app_secret="local-rehearsal-application-secret!",
                            demo_user_email="user@example.invalid", demo_user_password="rehearsal-pass",
                            demo_ops_email="ops@example.invalid", demo_ops_password="rehearsal-pass",
                            analysis_per_minute=120, reports_per_minute=60, llm_calls_per_day=0, safe_browsing_key="",
                            website_public_html_enabled=False, fraud_url_model_path="")
        with TestClient(create_app(settings)) as client:
            result = run(client)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
