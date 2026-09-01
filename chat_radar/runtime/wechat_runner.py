"""微信 ingest 编排."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from chat_radar.config import ConfigStore
from chat_radar.core.models import RawMessage
from chat_radar.core.paths import data_dir, reports_dir
from chat_radar.filter import RuleEngine
from chat_radar.ingest.persist import append_messages
from chat_radar.ingest.wechat_export import parse_export_file
from chat_radar.ingest.wechat_inbox import scan_inbox_dir
from chat_radar.reporting.digest import DigestMeta, render_digest_markdown


def _raw_messages_path() -> Path:
    return data_dir() / "raw_messages.jsonl"


def _jobs_path() -> Path:
    return data_dir() / "jobs.jsonl"


def _wechat_enabled(cfg: ConfigStore) -> bool:
    return bool(cfg.get("wechat.enabled", False))


def _rule_engine(cfg: ConfigStore) -> RuleEngine:
    return RuleEngine(
        include_keywords=cfg.get("filter.include_keywords", []) or [],
        exclude_keywords=cfg.get("filter.exclude_keywords", []) or [],
        include_patterns=cfg.get("filter.include_patterns", []) or [],
    )


def run_wechat_parse(cfg: ConfigStore, file_path: str, *, chat_title: str | None = None) -> int:
    if not _wechat_enabled(cfg):
        print("错误：wechat.enabled 未开启，请在 chat_radar_config.json 设置 wechat.enabled=true", file=sys.stderr)
        return 1

    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        print(f"错误：文件不存在: {path}", file=sys.stderr)
        return 1

    title = chat_title or cfg.get("wechat.default_chat", path.stem)
    tz = cfg.get("report.timezone", "Asia/Shanghai")
    messages = parse_export_file(path, chat_title=title, timezone_name=tz)
    if not messages:
        print(f"未解析到消息: {path}", file=sys.stderr)
        return 1

    written, skipped = append_messages(_raw_messages_path(), messages)
    print(f"wechat parse: {path.name} → 解析 {len(messages)} 条，写入 {written}，跳过重复 {skipped}")
    return 0


def run_wechat_inbox(cfg: ConfigStore) -> int:
    if not _wechat_enabled(cfg):
        print("错误：wechat.enabled 未开启", file=sys.stderr)
        return 1

    inbox = Path(cfg.get("wechat.inbox_dir", "data/wechat_inbox"))
    if not inbox.is_absolute():
        inbox = data_dir().parent / inbox
    tz = cfg.get("report.timezone", "Asia/Shanghai")
    default_chat = cfg.get("wechat.default_chat", "inbox")
    messages = scan_inbox_dir(inbox, default_chat=default_chat, timezone_name=tz)
    if not messages:
        print(f"inbox 为空或无可解析文件: {inbox}")
        return 0

    written, skipped = append_messages(_raw_messages_path(), messages)
    print(f"wechat inbox: 扫描 {len(messages)} 条，写入 {written}，跳过重复 {skipped}")
    return 0


def _load_recent_wechat_messages(since_hours: int | None) -> list[RawMessage]:
    path = _raw_messages_path()
    if not path.exists():
        return []

    cutoff = None
    if since_hours is not None:
        cutoff = datetime.now(timezone.utc).timestamp() - since_hours * 3600

    out: list[RawMessage] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            if data.get("source") != "wechat":
                continue
            msg = RawMessage.from_json(data)
            if cutoff is not None:
                try:
                    ts = datetime.fromisoformat(msg.date.replace("Z", "+00:00")).timestamp()
                except ValueError:
                    continue
                if ts < cutoff:
                    continue
            out.append(msg)
    return out


def _title_from_text(text: str) -> str:
    first = text.strip().splitlines()[0] if text.strip() else "（无标题）"
    return first[:80]


def run_wechat_digest(cfg: ConfigStore, *, since_hours: int | None = 24) -> int:
    if not _wechat_enabled(cfg):
        print("错误：wechat.enabled 未开启", file=sys.stderr)
        return 1

    messages = _load_recent_wechat_messages(since_hours)
    engine = _rule_engine(cfg)
    summary_max = int(cfg.get("report.summary_max_chars", 300))

    jobs: list[dict] = []
    for msg in messages:
        result = engine.evaluate(msg.text)
        if not result.matched:
            continue
        jobs.append(
            {
                "title": _title_from_text(msg.text),
                "channel_username": msg.chat_title or msg.source_id,
                "sender": msg.sender,
                "date": msg.date,
                "matched_rules": result.rules,
                "link": msg.link,
                "summary": msg.text[:summary_max],
                "source": "wechat",
            }
        )

    jobs.sort(key=lambda j: j.get("date", ""), reverse=True)
    meta = DigestMeta(
        scanned_channels=len({m.chat_title for m in messages}),
        total_fetched=len(messages),
        total_matched=len(jobs),
        generated_at=datetime.now(timezone.utc),
    )
    md = render_digest_markdown(meta, jobs, summary_max=summary_max, title_prefix="CHAT-RADAR")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = reports_dir() / f"DIGEST_wechat_{ts}.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"wechat digest: 消息 {len(messages)}，命中 {len(jobs)} → {out_path}")
    return 0
