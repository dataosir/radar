"""关键词 / 正则招聘帖过滤."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class FilterResult:
    matched: bool
    rules: list[str] = field(default_factory=list)
    reason: str = ""


class RuleEngine:
    def __init__(
        self,
        include_keywords: list[str],
        exclude_keywords: list[str],
        include_patterns: list[str] | None = None,
    ) -> None:
        self._include = [k.strip() for k in include_keywords if k.strip()]
        self._exclude = [k.strip() for k in exclude_keywords if k.strip()]
        self._patterns = [re.compile(p, re.IGNORECASE) for p in (include_patterns or [])]

    def evaluate(self, text: str) -> FilterResult:
        if not text or not text.strip():
            return FilterResult(False, reason="空消息")

        lower = text.lower()
        for word in self._exclude:
            if word.lower() in lower:
                return FilterResult(False, rules=[f"exclude:{word}"], reason=f"命中排除词: {word}")

        hits: list[str] = []
        for word in self._include:
            if word.lower() in lower:
                hits.append(f"include:{word}")

        for i, pat in enumerate(self._patterns):
            if pat.search(text):
                hits.append(f"pattern:{i}")

        if hits:
            return FilterResult(True, rules=hits, reason="命中正向规则")

        return FilterResult(False, reason="未命中任何正向词")
