"""Hybrid score (risk-scoring.md): rule_score from text rules + evidence, blended with the LLM level.

Evidence weights:
| Signal                         | Points | Source                                                       |
|--------------------------------|--------|--------------------------------------------------------------|
| domain_check high / medium     | +45/+20| risk-scoring.md (worst URL counts once; shortener = medium)  |
| official domain (whitelist)    | -30    | risk-scoring.md (once; only if no risky URL / blocklist hit)   |
| community blocklist hit        | +45    | PM 2026-11-26 — third-party, not ops-approved, frozen 2025-04-11, so      |
|                                |        | below "danh sách đen ĐÃ DUYỆT" (+60). Alone -> medium.          |
"""
from __future__ import annotations

from .evidence import EvidenceItem
from .rules import TextRuleResult

LLM_SCORE = {"high": 80, "medium": 50, "uncertain": 30, "low": 15}
P_DOMAIN = {"high": 45, "medium": 20}
P_COMMUNITY_BLACKLIST = 45
P_OFFICIAL = -30


def evidence_points(items: list[EvidenceItem]) -> list[tuple[EvidenceItem, int]]:
    """(item, points) for items that contribute to rule_score."""
    out: list[tuple[EvidenceItem, int]] = []
    worst = None
    for it in items:
        if it.signal in ("domain_high", "domain_medium"):
            if worst is None or P_DOMAIN[it.level] > P_DOMAIN[worst.level]:
                worst = it
    if worst is not None:
        out.append((worst, P_DOMAIN[worst.level]))
    bl = next((it for it in items if it.signal == "community_blacklist"), None)
    if bl is not None:
        out.append((bl, P_COMMUNITY_BLACKLIST))
    official = next((it for it in items if it.signal == "official_domain"), None)
    if official is not None and worst is None and bl is None:
        out.append((official, P_OFFICIAL))
    return out


def rule_score(text_res: TextRuleResult, items: list[EvidenceItem]) -> int:
    total = text_res.score + sum(p for _, p in evidence_points(items))
    return max(0, min(100, total))


def blend(rule: int, llm_level: str | None) -> tuple[int, str]:
    """Exactly risk-scoring.md: disagreement -> higher level; LLM missing -> uncertain, never low."""
    llm = LLM_SCORE.get(llm_level, 0) if llm_level else 0
    final = max(rule, llm)
    if final >= 60:
        level = "high"
    elif final >= 35:
        level = "medium"
    elif llm_level in ("uncertain", None):
        level = "uncertain"
    else:
        level = "low"
    return final, level
