"""按联系人维度渲染微信聊天记录 Markdown 摘要."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

from chat_radar.core.models import RawMessage, stable_hash
from chat_radar.ingest.wechat_db_reader import is_plain_text_content

_GROUP_CHAT_MARKER = "@chatroom"
_INVALID_FILENAME_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def is_group_message(msg: RawMessage) -> bool:
    """判断消息是否来自群聊."""
    if msg.link and _GROUP_CHAT_MARKER in msg.link:
        return True
    return False


def person_key(msg: RawMessage, *, self_name: str = "我") -> str:
    """将消息归到联系人维度（群聊按发言人，私聊按会话对象）."""
    if is_group_message(msg):
        sender = (msg.sender or "").strip()
        if sender and sender != self_name:
            return sender
        return sender or "未知"
    title = (msg.chat_title or "").strip()
    if title:
        return title
    sender = (msg.sender or "").strip()
    if sender and sender != self_name:
        return sender
    return "未知"


def filter_plain_text_messages(messages: Iterable[RawMessage]) -> list[RawMessage]:
    """仅保留纯文本消息（跳过图片/语音/链接/XML 等）."""
    out: list[RawMessage] = []
    for msg in messages:
        if msg.has_media:
            continue
        if not is_plain_text_content(msg.text):
            continue
        out.append(msg)
    return out


def group_messages_by_person(
    messages: Iterable[RawMessage],
    *,
    self_name: str = "我",
) -> dict[str, list[RawMessage]]:
    """按联系人聚合消息，每人内按时间升序."""
    buckets: dict[str, list[RawMessage]] = defaultdict(list)
    for msg in messages:
        key = person_key(msg, self_name=self_name)
        buckets[key].append(msg)
    for person, items in buckets.items():
        items.sort(key=lambda m: m.date)
    return dict(sorted(buckets.items(), key=lambda kv: kv[0]))


def _parse_date(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _format_date_short(value: str) -> str:
    dt = _parse_date(value)
    if dt is None:
        return value
    return dt.strftime("%Y-%m-%d %H:%M")


def _safe_filename(name: str) -> str:
    cleaned = _INVALID_FILENAME_RE.sub("_", name.strip())
    cleaned = cleaned.strip(". ") or "unknown"
    return cleaned[:120]


def _chat_sections(messages: list[RawMessage], *, body_max_chars: int) -> list[str]:
    by_chat: dict[str, list[RawMessage]] = defaultdict(list)
    for msg in messages:
        chat = (msg.chat_title or "未知会话").strip()
        by_chat[chat].append(msg)

    lines: list[str] = []
    for chat_title, chat_msgs in sorted(by_chat.items(), key=lambda kv: kv[0]):
        lines.append(f"### {chat_title}（{len(chat_msgs)} 条）")
        lines.append("")
        for msg in chat_msgs:
            when = _format_date_short(msg.date)
            body = (msg.text or "").strip()
            if len(body) > body_max_chars:
                body = body[:body_max_chars] + "…"
            body = body.replace("\n", " / ")
            if is_group_message(msg):
                sender = (msg.sender or "未知").strip()
                lines.append(f"- `{when}` **{sender}**：{body or '（空）'}")
            else:
                lines.append(f"- `{when}` {body or '（空）'}")
        lines.append("")
    return lines


def render_person_markdown(
    person: str,
    messages: list[RawMessage],
    *,
    generated_at: datetime,
    body_max_chars: int = 500,
    self_name: str = "我",
) -> str:
    """渲染单个联系人的 Markdown 文档."""
    if not messages:
        return f"# {person} · 聊天记录\n\n_无消息_\n"

    dates = [d for m in messages if (d := _parse_date(m.date)) is not None]
    date_min = min(dates).strftime("%Y-%m-%d") if dates else "—"
    date_max = max(dates).strftime("%Y-%m-%d") if dates else "—"
    chats = sorted({(m.chat_title or "未知会话") for m in messages})
    group_count = sum(1 for m in messages if is_group_message(m))
    private_count = len(messages) - group_count

    lines = [
        f"# {person} · 聊天记录摘要",
        "",
        f"> 生成时间：{generated_at.strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 概览",
        "",
        f"- **消息总数**：{len(messages)}",
        f"- **时间范围**：{date_min} ~ {date_max}",
        f"- **涉及会话**：{len(chats)} 个",
        f"- **群聊消息**：{group_count} 条",
        f"- **私聊消息**：{private_count} 条",
        f"- **内容类型**：纯文本",
        "",
        "## 会话列表",
        "",
    ]
    for chat in chats:
        count = sum(1 for m in messages if (m.chat_title or "未知会话") == chat)
        lines.append(f"- {chat}（{count} 条）")
    lines.append("")
    lines.append("## 消息时间线（按会话分组）")
    lines.append("")
    lines.extend(_chat_sections(messages, body_max_chars=body_max_chars))
    return "\n".join(lines).rstrip() + "\n"


def render_contacts_index(
    grouped: dict[str, list[RawMessage]],
    *,
    generated_at: datetime,
    output_dir: Path,
    filename_map: dict[str, str] | None = None,
) -> str:
    """渲染联系人索引页."""
    lines = [
        "# 微信联系人聊天记录索引",
        "",
        f"> 生成时间：{generated_at.strftime('%Y-%m-%d %H:%M')}",
        "",
        f"- **联系人数**：{len(grouped)}",
        f"- **消息总数**：{sum(len(v) for v in grouped.values())}",
        "",
        "## 联系人",
        "",
        "| 联系人 | 消息数 | 文档 |",
        "|---|---:|---|",
    ]
    for person, msgs in grouped.items():
        filename = (filename_map or {}).get(person) or f"{_safe_filename(person)}.md"
        lines.append(f"| {person} | {len(msgs)} | [{filename}]({filename}) |")
    lines.append("")
    lines.append(f"_输出目录：`{output_dir}`_")
    lines.append("")
    return "\n".join(lines)


def _unique_output_path(output_dir: Path, person: str, used_names: set[str]) -> str:
    """生成唯一文件名，避免同名联系人覆盖."""
    base = _safe_filename(person)
    fname = f"{base}.md"
    if fname in used_names:
        fname = f"{base}_{stable_hash(person)[:8]}.md"
    used_names.add(fname)
    return fname


def write_person_summaries(
    grouped: dict[str, list[RawMessage]],
    output_dir: Path,
    *,
    generated_at: datetime,
    body_max_chars: int = 500,
    self_name: str = "我",
    only_person: str | None = None,
) -> list[Path]:
    """写入每人一份 Markdown，并生成 index.md."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    targets = grouped
    if only_person:
        key = only_person.strip()
        targets = {k: v for k, v in grouped.items() if k == key}
        if not targets:
            raise ValueError(f"未找到联系人: {only_person}")

    filename_map: dict[str, str] = {}
    used_names: set[str] = set()
    for person in targets:
        filename_map[person] = _unique_output_path(output_dir, person, used_names)

    for person, messages in targets.items():
        md = render_person_markdown(
            person,
            messages,
            generated_at=generated_at,
            body_max_chars=body_max_chars,
            self_name=self_name,
        )
        path = output_dir / filename_map[person]
        path.write_text(md, encoding="utf-8")
        written.append(path)

    if not only_person:
        index_md = render_contacts_index(
            grouped,
            generated_at=generated_at,
            output_dir=output_dir,
            filename_map=filename_map,
        )
        index_path = output_dir / "index.md"
        index_path.write_text(index_md, encoding="utf-8")
        written.append(index_path)

    return written
