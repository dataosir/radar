"""JSONL 持久化与去重."""

from __future__ import annotations

import json
from pathlib import Path

from chat_radar.core.models import RawMessage


def load_dedup_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    if not path.exists():
        return keys
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            source = data.get("source", "telegram")
            source_id = str(data.get("source_id", data.get("channel_id", "")))
            message_id = str(data.get("message_id", ""))
            keys.add(f"{source}:{source_id}:{message_id}")
    return keys


def append_messages(path: Path, messages: list[RawMessage], *, dedup: bool = True) -> tuple[int, int]:
    """追加消息到 JSONL。返回 (写入条数, 跳过重复条数)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_dedup_keys(path) if dedup else set()
    written = 0
    skipped = 0
    with path.open("a", encoding="utf-8") as fh:
        for msg in messages:
            key = msg.dedup_key
            if dedup and key in existing:
                skipped += 1
                continue
            fh.write(json.dumps(msg.to_json(), ensure_ascii=False) + "\n")
            existing.add(key)
            written += 1
    return written, skipped
