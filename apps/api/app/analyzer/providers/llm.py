import json
import re

import httpx

from ...config import ROOT

PROMPT = (ROOT / "prompts" / "analyzer_signals_v1.md").read_text(encoding="utf-8")
V0 = (ROOT / "prompts" / "analyzer_v0.md").read_text(encoding="utf-8")
TAXONOMY = V0.split("TAXONOMY RÚT GỌN", 1)[1].split("YÊU CẦU ĐẦU RA", 1)[0]
SCENARIOS = frozenset(re.findall(r"^  (G[1-5]\.\d+) ", TAXONOMY, re.M))
RISK = {"high": 80, "medium": 50, "uncertain": 30, "low": 15}
PROMPT_VERSION = "signals-v1"


def infer(matches, evidence, benign, settings, limits):
    if not (settings.llm_base_url and settings.llm_model):
        return None
    # Only application-authored descriptions can enter the provider request.
    facts = {
        "signals": [rule.finding for rule, _ in matches],
        "verified_sources": [
            {"source": item["source"], "weight": item["weight"]} for item in evidence
        ],
        "familiar_benign_pattern": benign,
    }
    for model in dict.fromkeys(filter(None, (settings.llm_model, settings.llm_fallback_model))):
        if not limits.take("llm-daily", settings.llm_calls_per_day, 86400):
            break
        try:
            response = httpx.post(
                settings.llm_base_url.rstrip("/") + "/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"} if settings.llm_api_key else {},
                json={"model": model, "temperature": 0, "max_tokens": 120,
                      "messages": [
                          {"role": "system", "content": PROMPT.replace("{{taxonomy}}", TAXONOMY)},
                          {"role": "user", "content": json.dumps(facts, ensure_ascii=False)},
                      ]},
                timeout=1.6,
            )
            response.raise_for_status()
            content = json.loads(response.json()["choices"][0]["message"]["content"])
            scenario = content["scenario_id"]
            if content["risk_level"] in RISK and (scenario is None or scenario in SCENARIOS):
                return model, content["risk_level"], scenario
        except (httpx.HTTPError, ValueError, IndexError, KeyError, TypeError):
            continue
    return None
