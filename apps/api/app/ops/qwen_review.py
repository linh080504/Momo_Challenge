from ..analyzer.providers.llm import QWEN_MODEL, query_qwen
from ..config import ROOT


PROMPT = (ROOT / "prompts" / "ops_review_v1.md").read_text(encoding="utf-8")


def suggest(context, agent, task, facts, options):
    payload = {"agent": agent, "task": task, "permission": "draft_only", "facts": facts, "options": options}
    result, status = query_qwen(context["settings"], context["limits"], PROMPT, payload, timeout=6.0)
    code = result.get("code") if isinstance(result, dict) and set(result) == {"code"} else None
    if isinstance(code, str) and code in options:
        return {"status": "ok", "model": QWEN_MODEL, "note": options[code]}
    return {"status": "invalid" if status == "ok" else status, "model": None, "note": None}
