"""离线自测 — 不联网."""

from __future__ import annotations

import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from chat_radar.filter import RuleEngine
from chat_radar.ingest.persist import append_messages, load_dedup_keys
from chat_radar.ingest.wechat_export import parse_export_text
from chat_radar.ingest.wechat_inbox import parse_inbox_file
from chat_radar.reporting import render_digest_markdown


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
    from chat_radar.reporting.digest import DigestMeta

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


def _check_wechat_export_parse() -> None:
    sample = """2026-09-01 10:30:15 HR小王
招聘 Java 后端，远程优先

2026-09-01 10:31:00 路人甲
今天天气不错
"""
    msgs = parse_export_text(sample, chat_title="Java招聘群")
    assert len(msgs) == 2
    assert msgs[0].sender == "HR小王"
    assert "Java" in msgs[0].text
    assert msgs[0].chat_title == "Java招聘群"
    assert msgs[0].source == "wechat"


def _check_wechat_inbox_frontmatter() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "msg.md"
        path.write_text(
            """---
chat: 远程招聘群
sender: Alice
date: 2026-09-01T10:00:00+08:00
---
GraalVM 架构师岗位，Remote OK
""",
            encoding="utf-8",
        )
        msgs = parse_inbox_file(path)
        assert len(msgs) == 1
        assert msgs[0].chat_title == "远程招聘群"
        assert "GraalVM" in msgs[0].text


def _check_persist_dedup() -> None:
    from chat_radar.core.models import RawMessage

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "raw.jsonl"
        m = RawMessage(
            source="wechat",
            source_id="chat1",
            message_id="m1",
            date="2026-09-01T00:00:00+00:00",
            text="test",
        )
        w1, s1 = append_messages(path, [m])
        w2, s2 = append_messages(path, [m])
        assert w1 == 1 and s1 == 0
        assert w2 == 0 and s2 == 1
        assert len(load_dedup_keys(path)) == 1


_CHECKS = [
    ("filter_include", _check_filter_include),
    ("filter_exclude", _check_filter_exclude),
    ("filter_empty", _check_filter_empty),
    ("digest_render", _check_digest_render),
    ("wechat_export_parse", _check_wechat_export_parse),
    ("wechat_inbox_frontmatter", _check_wechat_inbox_frontmatter),
    ("persist_dedup", _check_persist_dedup),
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
