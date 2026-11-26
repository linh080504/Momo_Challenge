"""Validate kết quả theo `.claude/skills/scam-analyzer/analysis.schema.json` (nguồn sự thật duy nhất)."""
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match


class AnalysisValidator:
    def __init__(self, schema_path: Path):
        schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        self._validator = Draft202012Validator(schema)

    def first_error(self, instance) -> str | None:
        """None nếu hợp lệ; ngược lại chuỗi `đường/dẫn: từ_khóa` — không chứa giá trị đầu vào (an toàn để log)."""
        error = best_match(self._validator.iter_errors(instance))
        if error is None:
            return None
        path = "/".join(str(p) for p in error.absolute_path) or "(root)"
        return f"{path}: {error.validator}"
