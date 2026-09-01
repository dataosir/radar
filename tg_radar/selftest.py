"""离线自测 — 不联网."""

from __future__ import annotations

import sys
from datetime import datetime, timezone

from tg_radar.filter import RuleEngine
from tg_radar.reporting import render_digest_markdown


def _check_filter_include() -> None:
    engine = RuleEngine(
        include_keywords=["Java", "远程"],
        exclude_keywords=["日结"],
    )
    r = engine.evaluate("招聘 Java 后端，支持远程办公")
    assert r.matched, r
    assert any("Java" in x for x in r.rules)


def _check_filter_exclude() -> None:
    engine = RuleEngine(include_keywords=["Java"], exclude_keywords=["日结"])
    r = engine.evaluate("Java 日结刷单")
    assert not r.matched, r
    assert r.rules, "应记录排除规则"


def _check_filter_empty() -> None:
    engine = RuleEngine(include_keywords=["Java"], exclude_keywords=[])
    r = engine.evaluate("   ")
    assert not r.matched


def _check_digest_render() -> None:
    from tg_radar.reporting.digest import DigestMeta

    md = render_digest_markdown(
        DigestMeta(1, 10, 1, datetime(2026, 9, 1, 8, 30, tzinfo=timezone.utc)),
        [
            {
                "title": "Java 远程",
                "channel_username": "@test",
                "date": "2026-09-01",
                "matched_rules": ["include:Java"],
                "link": "https://t.me/test/1",
                "summary": "hello",
            }
        ],
    )
    assert "Java 远程" in md
    assert "命中招聘：1" in md


_CHECKS = [
    ("filter_include", _check_filter_include),
    ("filter_exclude", _check_filter_exclude),
    ("filter_empty", _check_filter_empty),
    ("digest_render", _check_digest_render),
]


def run_selftest() -> int:
    failed = []
    for name, fn in _CHECKS:
        try:
            fn()
            print(f"  OK  {name}")
        except Exception as exc:
            print(f"  FAIL {name}: {exc}")
            failed.append(name)
    total = len(_CHECKS)
    passed = total - len(failed)
    print(f"\nselftest: {passed}/{total} 通过")
    return 0 if not failed else 3


if __name__ == "__main__":
    sys.exit(run_selftest())
