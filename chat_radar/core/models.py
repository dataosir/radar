"""跨源统一消息模型."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(*parts: str) -> str:
    payload = "\x1f".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass
class RawMessage:
    """Telegram / 微信统一原始消息."""

    source: str  # "telegram" | "wechat"
    source_id: str  # channel_id 或 chat 标识
    message_id: str
    date: str  # ISO8601
    text: str
    link: str = ""
    sender: str | None = None
    chat_title: str | None = None
    has_media: bool = False
    fetched_at: str = field(default_factory=utc_now_iso)

    @property
    def dedup_key(self) -> str:
        return f"{self.source}:{self.source_id}:{self.message_id}"

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> RawMessage:
        return cls(
            source=str(data.get("source", "telegram")),
            source_id=str(data.get("source_id", data.get("channel_id", ""))),
            message_id=str(data.get("message_id", "")),
            date=str(data["date"]),
            text=str(data.get("text", "")),
            link=str(data.get("link", "")),
            sender=data.get("sender"),
            chat_title=data.get("chat_title"),
            has_media=bool(data.get("has_media", False)),
            fetched_at=str(data.get("fetched_at", utc_now_iso())),
        )
