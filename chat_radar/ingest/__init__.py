"""Layer 2 · 多源 ingest 适配器."""

from chat_radar.ingest.cursors import get_last_message_id, load_cursors, save_cursors, update_cursor
from chat_radar.ingest.persist import append_messages, load_dedup_keys
from chat_radar.ingest.telethon_client import TelegramIngestor, build_telegram_link, message_to_raw

__all__ = [
    "TelegramIngestor",
    "append_messages",
    "build_telegram_link",
    "get_last_message_id",
    "load_cursors",
    "load_dedup_keys",
    "message_to_raw",
    "save_cursors",
    "update_cursor",
]
