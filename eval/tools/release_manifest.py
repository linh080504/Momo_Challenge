"""Record and recheck the exact inputs of an evaluation or release rehearsal."""
import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TRACKED_INPUTS = ("apps/api", "apps/web", "infra", "prompts", ".github/workflows", "compose.yaml",
                  "compose.staging.yaml", "compose.speech.yaml", "eval/tools",
                  ".claude/skills/eval-harness", ".claude/skills/evidence-tools", ".claude/skills/pii-guard")


def sha256(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def describe_checkout():
    paths = subprocess.check_output(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard",
                                     "--", *TRACKED_INPUTS], cwd=ROOT).decode("utf-8").split("\0")
    sources = {entry: sha256(ROOT / entry) for entry in sorted(set(paths) - {""}) if (ROOT / entry).is_file()}
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    return revision, sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("record", "verify"))
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--artifact", action="append", type=Path, default=[])
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    summary = report.get("summary", report)
    dataset_sha256 = sha256(args.dataset)
    if summary.get("dataset_sha256") != dataset_sha256:
        parser.error("Báo cáo không khớp checksum của dataset")
    revision, sources = describe_checkout()
    current = {
        "schema_version": 1,
        "git_revision": revision,
        "files": sources,
        "dataset_sha256": dataset_sha256,
        "report_sha256": sha256(args.report),
        "artifact_sha256": sorted(sha256(path) for path in args.artifact),
        "results": {key: summary.get(key) for key in
                    ("mode", "n", "synthetic_count", "models", "prompt_versions", "gates", "passed")},
    }
    if args.command == "record":
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        with args.manifest.open("x", encoding="utf-8") as target:
            json.dump({**current, "recorded_at": datetime.now(timezone.utc).isoformat()},
                      target, ensure_ascii=False, indent=2)
            target.write("\n")
        print(args.manifest)
    else:
        previous = json.loads(args.manifest.read_text(encoding="utf-8"))
        for key, value in current.items():
            if previous.get(key) != value:
                parser.error(f"Manifest không khớp ở mục {key}")
        print("Verified source, dataset, report and artifact checksums.")


if __name__ == "__main__":
    main()
