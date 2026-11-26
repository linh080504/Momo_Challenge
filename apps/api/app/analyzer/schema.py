"""analysis.schema.json validation.

The bundled copy (analysis.schema.json next to this file) must equal the source of truth
.claude/skills/scam-analyzer/analysis.schema.json — enforced by test_pipeline.py. It is bundled so
the API image does not depend on the .claude/ folder.
"""
from __future__ import annotations

import functools
import json
import pathlib

import jsonschema

SCHEMA_PATH = pathlib.Path(__file__).with_name("analysis.schema.json")


@functools.lru_cache(maxsize=1)
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=1)
def _validator() -> jsonschema.Draft202012Validator:
    s = schema()
    jsonschema.Draft202012Validator.check_schema(s)
    return jsonschema.Draft202012Validator(s)


def errors(instance) -> list[str]:
    """Human-readable validation errors ([] = valid). Messages may echo values: do not log them raw."""
    out = []
    for e in sorted(_validator().iter_errors(instance), key=lambda e: list(e.path)):
        where = "/".join(str(p) for p in e.path) or "(root)"
        out.append(f"{where}: {e.message[:200]}")
    return out


def is_valid(instance) -> bool:
    return not errors(instance)
