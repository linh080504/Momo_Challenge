import pathlib
import sys

API_ROOT = pathlib.Path(__file__).resolve().parents[3]  # apps/api
REPO_ROOT = API_ROOT.parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

SOURCE_SCHEMA = REPO_ROOT / ".claude" / "skills" / "scam-analyzer" / "analysis.schema.json"
