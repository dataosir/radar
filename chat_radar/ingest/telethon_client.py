"""Telethon 拉取适配器（F01）."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from telethon import TelegramClient
from telethon.errors import FloodWaitError, SessionPasswordNeededError
from telethon.tl.custom.message import Message

from chat_radar.core.models import RawMessage, utc_now_iso
from chat_radar.ingest.cursors import get_last_message_id, load_cursors

logger = logging.getLogger("chat_radar")


class TelegramNotLoggedInError(RuntimeError):
    """Telegram session 未授权，需先运行 auth."""


def session_file(base_dir: Path, session_name: str) -> Path:
    return base_dir / session_name


def session_storage_path(base_dir: Path, session_name: str) -> Path:
    """Telethon 实际落盘的 .session 文件路径."""
    path = session_file(base_dir, session_name)
    if path.suffix == ".session":
        return path
    return path.with_suffix(".session")


def build_telegram_link(entity: Any, message_id: int) -> str:
    username = getattr(entity, "username", None)
    if username:
        return f"https://t.me/{username}/{message_id}"
    cid = int(entity.id)
    internal = str(cid)
    if internal.startswith("-100"):
        internal = internal[4:]
    else:
        internal = str(abs(cid))
    return f"https://t.me/c/{internal}/{message_id}"


def _message_date_iso(message: Message) -> str:
    from datetime import timezone

    dt = message.date
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def message_to_raw(entity: Any, message: Message) -> RawMessage:
    text = (message.message or "").strip()
    has_media = message.media is not None
    username = getattr(entity, "username", None)
    title = getattr(entity, "title", None) or username or str(entity.id)
    return RawMessage(
        source="telegram",
        source_id=str(entity.id),
        message_id=str(message.id),
        date=_message_date_iso(message),
        text=text,
        link=build_telegram_link(entity, message.id),
        chat_title=title,
        has_media=has_media and not text,
        fetched_at=utc_now_iso(),
    )


class TelegramIngestor:
    def __init__(
        self,
        *,
        api_id: int,
        api_hash: str,
        session_path: Path,
        data_dir: Path,
        bootstrap_limit: int = 50,
        request_delay_seconds: float = 1.0,
    ) -> None:
        self._api_id = api_id
        self._api_hash = api_hash
        self._session_path = session_path
        self._data_dir = data_dir
        self._bootstrap_limit = bootstrap_limit
        self._request_delay = request_delay_seconds
        self._client: TelegramClient | None = None
        self._cursors_path = data_dir / "cursors.json"

    @property
    def client(self) -> TelegramClient:
        if self._client is None:
            raise RuntimeError("Telegram 客户端未连接，请先调用 connect()")
        return self._client

    async def connect(self) -> None:
        self._client = TelegramClient(str(self._session_path), self._api_id, self._api_hash)
        await self._client.connect()
        if not await self._client.is_user_authorized():
            raise TelegramNotLoggedInError(
                "Telegram 尚未登录。请运行 ./start.sh auth（或菜单选「2) Telegram 登录」）"
            )

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.disconnect()
            self._client = None

    async def interactive_login(self) -> None:
        self._client = TelegramClient(str(self._session_path), self._api_id, self._api_hash)
        await self._client.connect()
        if await self._client.is_user_authorized():
            me = await self._client.get_me()
            print(f"已登录: {me.first_name} (id={me.id})")
            return
        phone = input("手机号（含国际区号，如 +86...）: ").strip()
        await self._client.send_code_request(phone)
        code = input("验证码: ").strip()
        try:
            await self._client.sign_in(phone, code)
        except SessionPasswordNeededError:
            password = input("两步验证密码: ").strip()
            await self._client.sign_in(password=password)
        me = await self._client.get_me()
        print(f"登录成功: {me.first_name} (id={me.id})")

    async def fetch_channel(self, channel: str, *, limit: int | None = None) -> list[RawMessage]:
        entity = await self._with_flood_retry(self.client.get_entity, channel)
        channel_id = str(entity.id)
        cursors = load_cursors(self._cursors_path)
        last_id = get_last_message_id(cursors, channel_id)

        if last_id is None:
            fetch_limit = limit if limit is not None else self._bootstrap_limit
            messages = await self._collect_messages(entity, limit=fetch_limit)
        else:
            messages = await self._collect_messages(entity, min_id=last_id, max_count=limit)

        messages.sort(key=lambda m: m.id)
        raw_list = [message_to_raw(entity, msg) for msg in messages if msg.id]
        if raw_list:
            max_id = max(int(m.message_id) for m in raw_list)
            logger.info("fetch channel=%s new=%s max_id=%s", channel, len(raw_list), max_id)
        else:
            logger.info("fetch channel=%s new=0", channel)
        return raw_list

    async def _collect_messages(
        self,
        entity: Any,
        *,
        limit: int | None = None,
        min_id: int | None = None,
        max_count: int | None = None,
    ) -> list[Message]:
        """拉取消息列表，遇 FloodWait 自动等待后重试整批拉取."""
        while True:
            try:
                messages: list[Message] = []
                kwargs: dict[str, Any] = {}
                if limit is not None:
                    kwargs["limit"] = limit
                if min_id is not None:
                    kwargs["min_id"] = min_id
                async for msg in self.client.iter_messages(entity, **kwargs):
                    messages.append(msg)
                    if max_count is not None and len(messages) >= max_count:
                        break
                return messages
            except FloodWaitError as exc:
                logger.warning("FloodWait %s 秒，等待后重试 iter_messages", exc.seconds)
                await asyncio.sleep(exc.seconds)

    async def _with_flood_retry(self, fn, *args, **kwargs):
        while True:
            try:
                return await fn(*args, **kwargs)
            except FloodWaitError as exc:
                logger.warning("FloodWait %s 秒，等待后重试", exc.seconds)
                await asyncio.sleep(exc.seconds)
