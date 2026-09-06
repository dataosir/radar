"""Telegram 频道游标读写."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from chat_radar.core.models import RawMessage, utc_now_iso
from chat_radar.core.utils import atomic_write_json


def cursors_path(data_root: Path) -> Path:
    return data_root / "cursors.json"


def load_cursors(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"游标文件必须是 JSON 对象: {path}")
    return data


def get_last_message_id(cursors: dict[str, dict[str, Any]], channel_id: str) -> int | None:
    entry = cursors.get(channel_id)
    if not entry:
        return None
    value = entry.get("last_message_id")
    if value is None:
        return None
    return int(value)


def update_cursor(cursors: dict[str, dict[str, Any]], channel_id: str, last_message_id: int) -> None:
    current = get_last_message_id(cursors, channel_id)
    if current is not None and last_message_id <= current:
        return
    cursors[channel_id] = {
        "last_message_id": last_message_id,
        "updated_at": utc_now_iso(),
    }


def save_cursors(path: Path, cursors: dict[str, dict[str, Any]]) -> None:
    atomic_write_json(path, cursors)


def commit_fetch_cursor(path: Path, messages: list[RawMessage]) -> int | None:
    """落盘成功后推进游标。返回写入的 max message_id，无消息时返回 None."""
    if not messages:
        return None
    channel_id = messages[0].source_id
    max_id = max(int(m.message_id) for m in messages)
    cursors = load_cursors(path)
    update_cursor(cursors, channel_id, max_id)
    save_cursors(path, cursors)
    return max_id
