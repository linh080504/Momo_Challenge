"""Contract test: analyze() output validates against the source-of-truth schema."""
import asyncio
import json

import jsonschema
from conftest import SOURCE_SCHEMA

from app.analyzer import AnalyzerError, analyze


def _validator():
    schema = json.loads(SOURCE_SCHEMA.read_text(encoding="utf-8"))
    return jsonschema.Draft202012Validator(schema)


def test_text_only_output_is_schema_valid():
    out = asyncio.run(analyze("Chuyển gấp 5 triệu vào STK 0123456789", None, None))
    errors = list(_validator().iter_errors(out))
    assert not errors, [e.message for e in errors]


def test_image_only_output_is_schema_valid():
    out = asyncio.run(analyze("", b"\x89PNG\r\n\x1a\n" + b"0" * 16, "image/png"))
    assert not list(_validator().iter_errors(out))


def test_quotes_are_verbatim_from_input():
    text = "Chuyển gấp 5 triệu vào STK 0123456789"
    out = asyncio.run(analyze(text, None, None))
    assert all(f["quote"] in text for f in out["red_flags"])


def test_analyzer_error_has_code_and_message():
    err = AnalyzerError("llm_timeout", "Hệ thống bận")
    assert err.code == "llm_timeout" and err.message == "Hệ thống bận"
