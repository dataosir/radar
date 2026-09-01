"""微信 PC 导出 TXT 解析器.

支持的典型格式::

    2026-09-01 10:30:15 张三
    招聘 Java 后端，远程优先

    2026-09-01 10:31:00 李四
    [图片]
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from chat_radar.core.models import RawMessage, stable_hash

# 2026-09-01 10:30:15 张三
_HEADER_RE = re.compile(
    r"^(\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?)\s+(.+?)\s*$"
)
_MEDIA_MARKERS = {"[图片]", "[视频]", "[语音]", "[文件]", "[链接]", "[动画表情]", "[名片]"}


def _parse_timestamp(raw: str, tz_name: str) -> str:
    raw = raw.strip().replace("/", "-")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(raw, fmt)
            local = dt.replace(tzinfo=ZoneInfo(tz_name))
            return local.astimezone(timezone.utc).isoformat()
        except ValueError:
            continue
    return datetime.now(timezone.utc).isoformat()


def _chat_id(chat_title: str) -> str:
    return stable_hash("wechat-chat", chat_title)


def parse_export_text(
    text: str,
    *,
    chat_title: str,
    timezone_name: str = "Asia/Shanghai",
) -> list[RawMessage]:
    """解析微信导出的纯文本聊天记录."""
    messages: list[RawMessage] = []
    lines = text.splitlines()
    i = 0
    chat_id = _chat_id(chat_title)

    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line or line.startswith("─") or "微信导出" in line:
            continue

        m = _HEADER_RE.match(line)
        if not m:
            continue

        ts_raw, sender = m.group(1), m.group(2).strip()
        body_lines: list[str] = []
        while i < len(lines):
            peek = lines[i].strip()
            if _HEADER_RE.match(peek):
                break
            if peek:
                body_lines.append(peek)
            i += 1

        body = "\n".join(body_lines).strip()
        has_media = body in _MEDIA_MARKERS or body.startswith("[")
        if not body and not has_media:
            continue

        iso_date = _parse_timestamp(ts_raw, timezone_name)
        msg_id = stable_hash(chat_id, iso_date, sender, body)
        messages.append(
            RawMessage(
                source="wechat",
                source_id=chat_id,
                message_id=msg_id,
                date=iso_date,
                text=body,
                link="",
                sender=sender,
                chat_title=chat_title,
                has_media=has_media,
            )
        )

    return messages


def parse_export_file(
    path: Path,
    *,
    chat_title: str | None = None,
    timezone_name: str = "Asia/Shanghai",
) -> list[RawMessage]:
    title = chat_title or path.stem
    text = path.read_text(encoding="utf-8", errors="replace")
    return parse_export_text(text, chat_title=title, timezone_name=timezone_name)
