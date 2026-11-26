import json
import re

import httpx

from ...config import ROOT

PROMPT = (ROOT / "prompts" / "analyzer_signals_v1.md").read_text(encoding="utf-8")
V0 = (ROOT / "prompts" / "analyzer_v0.md").read_text(encoding="utf-8")
TAXONOMY = V0.split("TAXONOMY RÚT GỌN", 1)[1].split("YÊU CẦU ĐẦU RA", 1)[0]
SCENARIOS = frozenset(re.findall(r"^  (G[1-5]\.\d+) ", TAXONOMY, re.M))
RISK = {"high": 80, "medium": 50, "uncertain": 30, "low": 15}
PROMPT_VERSION = "signals-v2"
QWEN_MODEL = "qwen4-max"
QWEN_RESPONSES_URL = "https://ap-southeast-1.maas.qwencloudapi.com/compatible-mode/v1/responses"
INSTRUCTIONS = PROMPT.replace("{{taxonomy}}", TAXONOMY)


def _qwen_output(model, facts_json, key):
    response = httpx.post(
        QWEN_RESPONSES_URL,
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": model,
            "instructions": INSTRUCTIONS,
            "input": facts_json,
            "max_output_tokens": 120,
            "reasoning": {"effort": "none"},
            "store": False,
        },
        timeout=3.2, follow_redirects=False,
    )
    response.raise_for_status()
    return "".join(
        part["text"]
        for item in response.json()["output"] if item["type"] == "message"
        for part in item["content"] if part["type"] == "output_text"
    )


def _chat_output(model, facts_json, settings):
    response = httpx.post(
        settings.llm_base_url.rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {settings.llm_api_key}"} if settings.llm_api_key else {},
        json={"model": model, "temperature": 0, "max_tokens": 120,
              "messages": [
                  {"role": "system", "content": INSTRUCTIONS},
                  {"role": "user", "content": facts_json},
              ]},
        timeout=1.6, follow_redirects=False,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def infer(matches, evidence, benign, settings, limits, guidance=()):
    qwen_key = settings.dashscope_api_key.get_secret_value().strip()
    use_qwen = bool(qwen_key) and not (settings.llm_base_url or settings.llm_model)
    if not use_qwen and not (settings.llm_base_url and settings.llm_model):
        return None
    primary_model = QWEN_MODEL if use_qwen else settings.llm_model
    # Only application-authored descriptions can enter the provider request.
    facts = {
        "signals": [rule.finding for rule, _ in matches],
        "verified_sources": [
            {"source": item["source"], "weight": item["weight"]} for item in evidence
        ],
        "familiar_benign_pattern": benign,
        "reference_guidance": list(guidance),
    }
    facts_json = json.dumps(facts, ensure_ascii=False)
    for model in dict.fromkeys(filter(None, (primary_model, settings.llm_fallback_model))):
        if not limits.take("llm-daily", settings.llm_calls_per_day, 86400):
            break
        try:
            output = _qwen_output(model, facts_json, qwen_key) if use_qwen else _chat_output(model, facts_json, settings)
            content = json.loads(output)
            scenario = content["scenario_id"]
            if content["risk_level"] in RISK and (scenario is None or scenario in SCENARIOS):
                return model, content["risk_level"], scenario
        except (httpx.HTTPError, ValueError, IndexError, KeyError, TypeError):
            continue
    return None
