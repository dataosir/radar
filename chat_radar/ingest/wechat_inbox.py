"""微信 inbox 文件夹解析 — 手动粘贴 / 转发落盘."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from chat_radar.core.models import RawMessage, stable_hash
from chat_radar.ingest.wechat_processed import list_pending_files, mark_processed

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    meta: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        meta[key.strip().lower()] = val.strip()
    body = text[m.end() :].strip()
    return meta, body


def _parse_date(raw: str | None, fallback: datetime, tz_name: str) -> str:
    if not raw:
        return fallback.astimezone(timezone.utc).isoformat()
    raw = raw.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo(tz_name))
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        return fallback.astimezone(timezone.utc).isoformat()


def parse_inbox_file(
    path: Path,
    *,
    default_chat: str = "inbox",
    timezone_name: str = "Asia/Shanghai",
) -> list[RawMessage]:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return []

    meta, body = _parse_frontmatter(text)
    if not body:
        body = text

    chat_title = meta.get("chat") or meta.get("group") or default_chat
    sender = meta.get("sender") or meta.get("from")
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=ZoneInfo(timezone_name))
    iso_date = _parse_date(meta.get("date"), mtime, timezone_name)

    chat_id = stable_hash("wechat-chat", chat_title)
    msg_id = stable_hash(chat_id, iso_date, sender or "", body, str(path.name))
    return [
        RawMessage(
            source="wechat",
            source_id=chat_id,
            message_id=msg_id,
            date=iso_date,
            text=body,
            link=f"file://{path.resolve()}",
            sender=sender,
            chat_title=chat_title,
            has_media=False,
        )
    ]


def scan_inbox_dir(
    inbox_dir: Path,
    *,
    default_chat: str = "inbox",
    timezone_name: str = "Asia/Shanghai",
    extensions: tuple[str, ...] = (".txt", ".md"),
    state_path: Path | None = None,
) -> list[RawMessage]:
    if not inbox_dir.exists():
        return []
    pending = (
        list_pending_files(inbox_dir, state_path=state_path, extensions=extensions)
        if state_path is not None
        else [p for p in sorted(inbox_dir.iterdir()) if p.is_file() and not p.name.startswith(".") and p.suffix.lower() in extensions]
    )
    messages: list[RawMessage] = []
    for path in pending:
        parsed = parse_inbox_file(
            path,
            default_chat=default_chat,
            timezone_name=timezone_name,
        )
        if not parsed:
            continue
        messages.extend(parsed)
        if state_path is not None:
            mark_processed(state_path, path)
    return messages
