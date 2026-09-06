"""离线自测 — 不联网."""

from __future__ import annotations

import sys
import json
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
    assert "扫描会话/频道" in md


def _check_merged_digest_sources() -> None:
    from chat_radar.core.models import RawMessage
    from chat_radar.filter import RuleEngine
    from chat_radar.ingest.persist import append_messages, load_recent_messages
    from chat_radar.reporting.digest import DigestMeta, render_digest_markdown

    with tempfile.TemporaryDirectory() as tmp:
        raw_path = Path(tmp) / "raw.jsonl"
        tg = RawMessage(
            source="telegram",
            source_id="-1001",
            message_id="1",
            date="2026-09-06T10:00:00+00:00",
            text="Java 远程岗位",
            chat_title="@jobs",
        )
        wx = RawMessage(
            source="wechat",
            source_id="123@chatroom",
            message_id="2",
            date="2026-09-06T11:00:00+00:00",
            text="招聘 Spring 后端",
            chat_title="招聘群",
            sender="HR",
        )
        append_messages(raw_path, [tg, wx])
        messages = load_recent_messages(raw_path, since_hours=48, sources={"telegram", "wechat"})
        assert len(messages) == 2

        engine = RuleEngine(include_keywords=["Java", "Spring"], exclude_keywords=[])
        jobs: list[dict] = []
        for msg in messages:
            result = engine.evaluate(msg.text)
            if not result.matched:
                continue
            jobs.append(
                {
                    "title": msg.text[:80],
                    "channel_username": msg.chat_title or msg.source_id,
                    "sender": msg.sender,
                    "date": msg.date,
                    "matched_rules": result.rules,
                    "link": msg.link,
                    "summary": msg.text,
                    "source": msg.source,
                }
            )
        assert len(jobs) == 2
        source_fetched = {"Telegram": 1, "微信": 1}
        source_matched = {"Telegram": 1, "微信": 1}
        md = render_digest_markdown(
            DigestMeta(
                2,
                2,
                2,
                datetime(2026, 9, 6, 8, 30, tzinfo=timezone.utc),
                source_fetched=source_fetched,
                source_matched=source_matched,
            ),
            jobs,
        )
        assert "Telegram 1" in md
        assert "微信 1" in md
        assert "telegram" in md
        assert "wechat" in md


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


def _check_cursors_roundtrip() -> None:
    import tempfile
    from pathlib import Path

    from chat_radar.ingest.cursors import get_last_message_id, load_cursors, save_cursors, update_cursor

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "cursors.json"
        cursors: dict = {}
        update_cursor(cursors, "123", 100)
        save_cursors(path, cursors)
        loaded = load_cursors(path)
        assert get_last_message_id(loaded, "123") == 100
        update_cursor(loaded, "123", 50)
        assert get_last_message_id(loaded, "123") == 100
        update_cursor(loaded, "123", 200)
        assert get_last_message_id(loaded, "123") == 200


def _check_commit_fetch_cursor() -> None:
    from chat_radar.core.models import RawMessage
    from chat_radar.ingest.cursors import commit_fetch_cursor, get_last_message_id, load_cursors

    with tempfile.TemporaryDirectory() as tmp:
        cursor_path = Path(tmp) / "cursors.json"
        msgs = [
            RawMessage(
                source="telegram",
                source_id="-100123",
                message_id="10",
                date="2026-09-01T00:00:00+00:00",
                text="a",
            ),
            RawMessage(
                source="telegram",
                source_id="-100123",
                message_id="20",
                date="2026-09-01T00:00:00+00:00",
                text="b",
            ),
        ]
        max_id = commit_fetch_cursor(cursor_path, msgs)
        assert max_id == 20
        loaded = load_cursors(cursor_path)
        assert get_last_message_id(loaded, "-100123") == 20


def _check_cursor_after_persist() -> None:
    """游标应在落盘成功后推进，模拟 fetch→append→commit 顺序."""
    from chat_radar.core.models import RawMessage
    from chat_radar.ingest.cursors import commit_fetch_cursor, get_last_message_id, load_cursors
    from chat_radar.ingest.persist import append_messages

    with tempfile.TemporaryDirectory() as tmp:
        raw_path = Path(tmp) / "raw.jsonl"
        cursor_path = Path(tmp) / "cursors.json"
        msg = RawMessage(
            source="telegram",
            source_id="-100999",
            message_id="55",
            date="2026-09-01T00:00:00+00:00",
            text="job post",
        )
        written, _ = append_messages(raw_path, [msg])
        assert written == 1
        commit_fetch_cursor(cursor_path, [msg])
        loaded = load_cursors(cursor_path)
        assert get_last_message_id(loaded, "-100999") == 55


def _check_telegram_link() -> None:
    from types import SimpleNamespace

    from chat_radar.ingest.telethon_client import build_telegram_link

    public = SimpleNamespace(id=-100123, username="jobs_cn")
    assert build_telegram_link(public, 42) == "https://t.me/jobs_cn/42"

    private = SimpleNamespace(id=-1001234567890, username=None)
    assert build_telegram_link(private, 99) == "https://t.me/c/1234567890/99"


def _check_session_storage_path() -> None:
    from chat_radar.ingest.telethon_client import session_storage_path

    assert session_storage_path(Path("/tmp/cr"), "chat_radar") == Path("/tmp/cr/chat_radar.session")
    assert session_storage_path(Path("/tmp/cr"), "foo.session") == Path("/tmp/cr/foo.session")


def _check_wechat_db_reader() -> None:
    import hashlib
    import sqlite3

    from chat_radar.ingest.wechat_db_reader import read_messages_from_decrypted

    username = "12345678@chatroom"
    table = "Msg_" + hashlib.md5(username.encode()).hexdigest()

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        contact_db = root / "contact" / "contact.db"
        contact_db.parent.mkdir(parents=True)
        conn = sqlite3.connect(contact_db)
        conn.execute("CREATE TABLE contact (username TEXT, nick_name TEXT, remark TEXT)")
        conn.execute(
            "INSERT INTO contact VALUES (?, ?, ?)",
            (username, "招聘群", ""),
        )
        conn.commit()
        conn.close()

        msg_db = root / "message" / "message_0.db"
        msg_db.parent.mkdir(parents=True)
        conn = sqlite3.connect(msg_db)
        conn.execute("CREATE TABLE Name2Id (rowid INTEGER PRIMARY KEY, user_name TEXT)")
        conn.execute("INSERT INTO Name2Id VALUES (1, 'wxid_sender')")
        conn.execute(
            f"""
            CREATE TABLE "{table}" (
                local_id INTEGER PRIMARY KEY,
                server_id INTEGER,
                local_type INTEGER,
                real_sender_id INTEGER,
                create_time INTEGER,
                message_content TEXT,
                WCDB_CT_message_content INTEGER
            )
            """
        )
        ts = int(datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc).timestamp())
        conn.execute(
            f'INSERT INTO "{table}" VALUES (1, 100, 1, 1, ?, ?, 0)',
            (ts, "wxid_sender:\n招聘 Java 后端"),
        )
        conn.execute(
            f'INSERT INTO "{table}" VALUES (2, 101, 3, 1, ?, ?, 0)',
            (ts + 120, "wxid_sender:\n<?xml version=\"1.0\"?><msg><img/></msg>"),
        )
        conn.commit()
        conn.close()

        msgs = read_messages_from_decrypted(root, since_hours=48, timezone_name="UTC")
        assert len(msgs) == 2
        assert "Java" in msgs[0].text
        assert msgs[0].chat_title == "招聘群"

        text_only = read_messages_from_decrypted(root, since_hours=48, timezone_name="UTC", text_only=True)
        assert len(text_only) == 1
        assert "Java" in text_only[0].text


def _check_wechat_private_db_reader() -> None:
    import hashlib
    import sqlite3

    from chat_radar.ingest.wechat_db_reader import read_messages_from_decrypted

    self_wxid = "wxid_self"
    peer = "wxid_peer"
    table = "Msg_" + hashlib.md5(peer.encode()).hexdigest()

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        contact_db = root / "contact" / "contact.db"
        contact_db.parent.mkdir(parents=True)
        conn = sqlite3.connect(contact_db)
        conn.execute("CREATE TABLE contact (username TEXT, nick_name TEXT, remark TEXT)")
        conn.execute("INSERT INTO contact VALUES (?, ?, ?)", (self_wxid, "我", ""))
        conn.execute("INSERT INTO contact VALUES (?, ?, ?)", (peer, "", "张三"))
        conn.commit()
        conn.close()

        msg_db = root / "message" / "message_0.db"
        msg_db.parent.mkdir(parents=True)
        conn = sqlite3.connect(msg_db)
        conn.execute("CREATE TABLE Name2Id (rowid INTEGER PRIMARY KEY, user_name TEXT)")
        conn.execute("INSERT INTO Name2Id VALUES (1, ?)", (self_wxid,))
        conn.execute("INSERT INTO Name2Id VALUES (2, ?)", (peer,))
        conn.execute(
            f"""
            CREATE TABLE "{table}" (
                local_id INTEGER PRIMARY KEY,
                server_id INTEGER,
                local_type INTEGER,
                real_sender_id INTEGER,
                create_time INTEGER,
                message_content TEXT,
                WCDB_CT_message_content INTEGER
            )
            """
        )
        ts = int(datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc).timestamp())
        conn.execute(
            f'INSERT INTO "{table}" VALUES (1, 100, 1, 2, ?, ?, 0)',
            (ts, "你好，请问还在招人吗？"),
        )
        conn.execute(
            f'INSERT INTO "{table}" VALUES (2, 101, 1, 1, ?, ?, 0)',
            (ts + 60, "在的，欢迎投递"),
        )
        conn.commit()
        conn.close()

        msgs = read_messages_from_decrypted(
            root,
            since_hours=48,
            timezone_name="UTC",
            scope="private",
            self_wxid=self_wxid,
            self_display_name="我",
        )
        assert len(msgs) == 2
        assert msgs[0].chat_title == "张三"
        assert msgs[0].sender == "张三"
        assert msgs[1].sender == "我"


def _check_wechat_person_summary() -> None:
    from datetime import timezone as tz

    from chat_radar.core.models import RawMessage
    from chat_radar.reporting.wechat_person_summary import (
        filter_plain_text_messages,
        group_messages_by_person,
        person_key,
        render_person_markdown,
        write_person_summaries,
    )

    group_msg = RawMessage(
        source="wechat",
        source_id="c1",
        message_id="m1",
        date="2026-09-06T10:00:00+08:00",
        text="招聘 Java",
        link="wechat-local:123@chatroom/1",
        sender="HR小王",
        chat_title="招聘群",
    )
    private_msg = RawMessage(
        source="wechat",
        source_id="c2",
        message_id="m2",
        date="2026-09-06T11:00:00+08:00",
        text="明天面试",
        link="wechat-local:wxid_peer/2",
        sender="张三",
        chat_title="张三",
    )
    assert person_key(group_msg) == "HR小王"
    assert person_key(private_msg) == "张三"

    media_msg = RawMessage(
        source="wechat",
        source_id="c1",
        message_id="m3",
        date="2026-09-06T10:05:00+08:00",
        text="[图片]\n<?xml version=\"1.0\"?><msg><img/></msg>",
        link="wechat-local:123@chatroom/3",
        sender="HR小王",
        chat_title="招聘群",
        has_media=True,
    )
    filtered = filter_plain_text_messages([group_msg, private_msg, media_msg])
    assert len(filtered) == 2

    grouped = group_messages_by_person([group_msg, private_msg])
    assert set(grouped.keys()) == {"HR小王", "张三"}

    md = render_person_markdown(
        "张三",
        grouped["张三"],
        generated_at=datetime(2026, 9, 6, 12, 0, tzinfo=tz.utc),
    )
    assert "张三 · 聊天记录摘要" in md
    assert "明天面试" in md

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        paths = write_person_summaries(
            grouped,
            out,
            generated_at=datetime(2026, 9, 6, 12, 0, tzinfo=tz.utc),
        )
        assert (out / "index.md").exists()
        assert len(paths) == 3


def _check_wechat_mac_paths() -> None:
    from chat_radar.ingest.wechat_mac_paths import discover_mac_wechat

    result = discover_mac_wechat()
    assert hasattr(result, "accounts")
    assert hasattr(result, "searched_roots")


def _check_wechat_read_stats() -> None:
    from chat_radar.ingest.wechat_db_reader import ReadStats

    stats = ReadStats(skipped_decompress=3, skipped_non_text=5)
    warnings = stats.warnings()
    assert any("zstd" in w for w in warnings)
    assert any("非纯文本" in w for w in warnings)


def _check_wechat_keys_inspect() -> None:
    import json

    from chat_radar.ingest.wechat_keys import inspect_keys_file

    with tempfile.TemporaryDirectory() as tmp:
        keys_path = Path(tmp) / "keys.json"
        keys_path.write_text(
            json.dumps({"_wxid": "wxid_test", "message/message_0.db": {"enc_key": "ab", "salt": "cd"}}),
            encoding="utf-8",
        )
        result = inspect_keys_file(keys_path)
        assert result.exists
        assert result.key_count == 1


def _check_wechat_filename_collision() -> None:
    from datetime import timezone as tz

    from chat_radar.core.models import RawMessage
    from chat_radar.reporting.wechat_person_summary import write_person_summaries

    msg_a = RawMessage(
        source="wechat",
        source_id="c1",
        message_id="m1",
        date="2026-09-06T10:00:00+08:00",
        text="A",
        link="wechat-local:wxid_a/1",
        sender="test/user",
        chat_title="群1",
    )
    msg_b = RawMessage(
        source="wechat",
        source_id="c2",
        message_id="m2",
        date="2026-09-06T11:00:00+08:00",
        text="B",
        link="wechat-local:wxid_b/2",
        sender="test:other",
        chat_title="群2",
    )
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        paths = write_person_summaries(
            {"test/user": [msg_a], "test:other": [msg_b]},
            out,
            generated_at=datetime(2026, 9, 6, 12, 0, tzinfo=tz.utc),
        )
        filenames = {p.name for p in paths if p.name != "index.md"}
        assert len(filenames) == 2


def _check_channels_crud() -> None:
    import tempfile

    from chat_radar.config import ConfigStore
    from chat_radar.config.channels import (
        channels_add,
        channels_remove,
        channels_set_enabled,
        find_channel_index,
        get_channels,
        normalize_channel_ref,
    )

    assert normalize_channel_ref("jobs") == "@jobs"
    assert normalize_channel_ref("@jobs") == "@jobs"
    assert normalize_channel_ref("-100123") == "-100123"

    with tempfile.TemporaryDirectory() as tmp:
        cfg = ConfigStore({})
        cfg_path = Path(tmp) / "cfg.json"

        channels_add(cfg, "jobs", note="test", enabled=True)
        assert len(get_channels(cfg)) == 1
        assert get_channels(cfg)[0]["username"] == "@jobs"

        channels_add(cfg, "@jobs", note="updated")
        assert len(get_channels(cfg)) == 1
        assert get_channels(cfg)[0]["note"] == "updated"

        channels_set_enabled(cfg, "jobs", enabled=False)
        assert not get_channels(cfg)[0]["enabled"]

        channels_add(cfg, "other", enabled=True)
        assert len(get_channels(cfg)) == 2
        idx = find_channel_index(get_channels(cfg), "other")
        assert idx == 1

        channels_remove(cfg, "@other")
        assert len(get_channels(cfg)) == 1

        cfg.save(cfg_path)
        loaded = ConfigStore(json.loads(cfg_path.read_text(encoding="utf-8")))
        assert len(get_channels(loaded)) == 1


def _check_wechat_export_watch() -> None:
    import tempfile
    from pathlib import Path

    from chat_radar.ingest.wechat_export_watch import scan_export_dir

    sample = """2026-09-01 10:30:15 张三
招聘 Java 后端
"""
    with tempfile.TemporaryDirectory() as tmp:
        export_dir = Path(tmp) / "exports"
        state = Path(tmp) / "state.json"
        export_dir.mkdir()
        f1 = export_dir / "群A.txt"
        f1.write_text(sample, encoding="utf-8")
        msgs, count = scan_export_dir(export_dir, state_path=state, default_chat="群A")
        assert count == 1
        assert len(msgs) == 1
        msgs2, count2 = scan_export_dir(export_dir, state_path=state, default_chat="群A")
        assert count2 == 0
        assert len(msgs2) == 0


def _check_wechat_inbox_processed() -> None:
    import tempfile
    from pathlib import Path

    from chat_radar.ingest.wechat_inbox import scan_inbox_dir
    from chat_radar.ingest.wechat_processed import is_processed, mark_processed

    with tempfile.TemporaryDirectory() as tmp:
        inbox = Path(tmp) / "inbox"
        state = Path(tmp) / "state.json"
        inbox.mkdir()
        f = inbox / "note.txt"
        f.write_text("hello paste", encoding="utf-8")
        assert not is_processed(state, f)
        first = scan_inbox_dir(inbox, state_path=state, default_chat="test")
        assert len(first) == 1
        assert is_processed(state, f)
        second = scan_inbox_dir(inbox, state_path=state, default_chat="test")
        assert len(second) == 0


_CHECKS = [
    ("filter_include", _check_filter_include),
    ("filter_exclude", _check_filter_exclude),
    ("filter_empty", _check_filter_empty),
    ("digest_render", _check_digest_render),
    ("merged_digest_sources", _check_merged_digest_sources),
    ("wechat_export_parse", _check_wechat_export_parse),
    ("wechat_inbox_frontmatter", _check_wechat_inbox_frontmatter),
    ("wechat_db_reader", _check_wechat_db_reader),
    ("wechat_private_db_reader", _check_wechat_private_db_reader),
    ("wechat_person_summary", _check_wechat_person_summary),
    ("wechat_mac_paths", _check_wechat_mac_paths),
    ("wechat_read_stats", _check_wechat_read_stats),
    ("wechat_keys_inspect", _check_wechat_keys_inspect),
    ("wechat_filename_collision", _check_wechat_filename_collision),
    ("wechat_export_watch", _check_wechat_export_watch),
    ("wechat_inbox_processed", _check_wechat_inbox_processed),
    ("channels_crud", _check_channels_crud),
    ("persist_dedup", _check_persist_dedup),
    ("cursors_roundtrip", _check_cursors_roundtrip),
    ("commit_fetch_cursor", _check_commit_fetch_cursor),
    ("cursor_after_persist", _check_cursor_after_persist),
    ("session_storage_path", _check_session_storage_path),
    ("telegram_link", _check_telegram_link),
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
