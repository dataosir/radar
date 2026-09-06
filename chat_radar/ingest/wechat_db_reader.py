"""从解密后的微信 SQLite 库读取聊天记录."""

from __future__ import annotations

import hashlib
import re
import shutil
import sqlite3
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from chat_radar.core.models import RawMessage, stable_hash

# local_type 低 16 位
_TYPE_TEXT = 1
_TYPE_IMAGE = 3
_TYPE_VOICE = 34
_TYPE_VIDEO = 43
_TYPE_APP = 49
_TYPE_SYSTEM = 10000

_MEDIA_TYPES = {_TYPE_IMAGE, _TYPE_VOICE, _TYPE_VIDEO}
_GROUP_SUFFIX = "@chatroom"
_WXID_PREFIX_RE = re.compile(r"^[\w-]+:\n", re.MULTILINE)
_MEDIA_PREFIX_RE = re.compile(r"^\[(图片|语音|视频|链接/小程序|类型\d+)\]")
_XML_START_RE = re.compile(r"^\s*<(?:\?xml|msg|appmsg)", re.IGNORECASE)


def is_plain_text_content(text: str) -> bool:
    """判断消息正文是否为可读纯文本（排除图片/语音/XML 等）."""
    body = (text or "").strip()
    if not body:
        return False
    if _XML_START_RE.match(body):
        return False
    if _MEDIA_PREFIX_RE.match(body):
        return False
    return True


def _chat_id(chat_title: str) -> str:
    return stable_hash("wechat-chat", chat_title)


def _msg_table_name(username: str) -> str:
    return "Msg_" + hashlib.md5(username.encode("utf-8")).hexdigest()


def _try_decompress_zstd(data: bytes) -> str | None:
    if not data:
        return ""
    zstd_bin = shutil.which("zstd")
    if not zstd_bin:
        return None
    proc = subprocess.run(
        [zstd_bin, "-d", "-q", "--stdout"],
        input=data,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    for enc in ("utf-8", "utf-8-sig"):
        try:
            return proc.stdout.decode(enc)
        except UnicodeDecodeError:
            continue
    return proc.stdout.decode("utf-8", errors="replace")


def _decode_message_content(raw: object, compress_type: int | None) -> str | None:
    if raw is None:
        return ""
    if compress_type == 4:
        blob = raw if isinstance(raw, (bytes, bytearray)) else str(raw).encode("utf-8", errors="replace")
        text = _try_decompress_zstd(blob)
        if text is None:
            return None
        return text
    if isinstance(raw, (bytes, bytearray)):
        for enc in ("utf-8", "utf-8-sig", "gb18030"):
            try:
                return bytes(raw).decode(enc)
            except UnicodeDecodeError:
                continue
        return bytes(raw).decode("utf-8", errors="replace")
    return str(raw)


def _parse_group_sender(text: str) -> tuple[str, str]:
    m = _WXID_PREFIX_RE.match(text)
    if not m:
        return "", text
    sender_id = m.group(0).rstrip(":\n")
    body = text[m.end() :]
    return sender_id, body


def _type_label(local_type: int) -> str:
    base = local_type & 0xFFFF
    if base == _TYPE_TEXT:
        return ""
    if base == _TYPE_IMAGE:
        return "[图片]"
    if base == _TYPE_VOICE:
        return "[语音]"
    if base == _TYPE_VIDEO:
        return "[视频]"
    if base == _TYPE_APP:
        return "[链接/小程序]"
    if base == _TYPE_SYSTEM:
        return ""
    return f"[类型{base}]"


def _load_contacts(contact_db: Path) -> dict[str, dict[str, str]]:
    if not contact_db.is_file():
        return {}
    conn = sqlite3.connect(f"file:{contact_db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT username, nick_name, remark FROM contact WHERE username IS NOT NULL"
        ).fetchall()
    except sqlite3.Error:
        return {}
    finally:
        conn.close()

    out: dict[str, dict[str, str]] = {}
    for row in rows:
        username = str(row["username"] or "")
        if not username:
            continue
        remark = str(row["remark"] or "").strip()
        nick = str(row["nick_name"] or "").strip()
        display = remark or nick or username
        out[username] = {"display": display, "nick_name": nick, "remark": remark}
    return out


def _display_name(contacts: dict[str, dict[str, str]], username: str) -> str:
    info = contacts.get(username)
    if info:
        return info["display"]
    return username


def _resolve_sender(
    contacts: dict[str, dict[str, str]],
    name2id: dict[int, str],
    sender_rowid: int | None,
    content: str,
    is_group: bool,
    *,
    self_wxid: str | None = None,
    self_display_name: str = "我",
    chat_partner: str = "",
) -> str:
    if is_group:
        wxid, _ = _parse_group_sender(content)
        if wxid:
            return _display_name(contacts, wxid)
    if sender_rowid is not None and sender_rowid in name2id:
        wxid = name2id[sender_rowid]
        if self_wxid and wxid == self_wxid:
            return self_display_name
        return _display_name(contacts, wxid)
    if not is_group and chat_partner:
        return chat_partner
    return "未知"


def _load_name2id(conn: sqlite3.Connection) -> dict[int, str]:
    try:
        rows = conn.execute("SELECT rowid, user_name FROM Name2Id").fetchall()
    except sqlite3.Error:
        return {}
    return {int(r[0]): str(r[1]) for r in rows if r[1]}


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (table,)
    ).fetchone()
    return row is not None


@dataclass
class ReadStats:
    """消息读取统计（用于诊断不完整数据）."""

    messages: int = 0
    chats_scanned: int = 0
    dbs_scanned: int = 0
    skipped_system: int = 0
    skipped_non_text: int = 0
    skipped_decompress: int = 0
    skipped_empty: int = 0
    skipped_time: int = 0
    db_errors: list[str] = field(default_factory=list)

    def warnings(self) -> list[str]:
        """生成人类可读警告."""
        out: list[str] = []
        if self.skipped_decompress:
            out.append(
                f"压缩消息跳过 {self.skipped_decompress} 条（安装 zstd: brew install zstd）"
            )
        if self.skipped_non_text:
            out.append(f"非纯文本跳过 {self.skipped_non_text} 条")
        if self.db_errors:
            out.append(f"数据库读取错误 {len(self.db_errors)} 个")
        return out


def _scope_matches(username: str, scope: str) -> bool:
    is_group = username.endswith(_GROUP_SUFFIX)
    if scope == "groups":
        return is_group
    if scope == "private":
        return not is_group
    return True


def read_messages_from_decrypted(
    decrypted_dir: Path,
    *,
    since_hours: int | None = 24,
    timezone_name: str = "Asia/Shanghai",
    chat_names: list[str] | None = None,
    groups_only: bool = True,
    scope: str | None = None,
    self_wxid: str | None = None,
    self_display_name: str = "我",
    text_only: bool = False,
    stats: ReadStats | None = None,
) -> list[RawMessage]:
    """从解密缓存目录读取消息，转为 RawMessage 列表."""
    effective_scope = scope or ("groups" if groups_only else "all")
    contact_db = decrypted_dir / "contact" / "contact.db"
    contacts = _load_contacts(contact_db)

    targets: list[tuple[str, str]] = []
    name_filter = {n.strip().lower() for n in (chat_names or []) if n.strip()}
    for username, info in contacts.items():
        if not _scope_matches(username, effective_scope):
            continue
        display = info["display"]
        if name_filter and display.lower() not in name_filter and username.lower() not in name_filter:
            continue
        targets.append((username, display))

    cutoff_ts: float | None = None
    if since_hours is not None:
        cutoff_ts = datetime.now(timezone.utc).timestamp() - since_hours * 3600

    tz = ZoneInfo(timezone_name)
    messages: list[RawMessage] = []
    read_stats = stats if stats is not None else ReadStats()

    msg_root = decrypted_dir / "message"
    if not msg_root.is_dir():
        return messages

    read_stats.chats_scanned = len(targets)

    for db_path in sorted(msg_root.glob("message_*.db")):
        if not db_path.is_file():
            continue
        read_stats.dbs_scanned += 1
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        except sqlite3.Error as exc:
            read_stats.db_errors.append(f"{db_path.name}: {exc}")
            continue
        try:
            name2id = _load_name2id(conn)
            for username, chat_title in targets:
                table = _msg_table_name(username)
                if not _table_exists(conn, table):
                    continue
                is_group = username.endswith(_GROUP_SUFFIX)
                chat_id = _chat_id(chat_title)
                try:
                    rows = conn.execute(
                        f"""
                        SELECT local_id, server_id, local_type, real_sender_id,
                               create_time, message_content, WCDB_CT_message_content
                        FROM "{table}"
                        ORDER BY create_time ASC
                        """
                    ).fetchall()
                except sqlite3.Error as exc:
                    read_stats.db_errors.append(f"{db_path.name}/{table}: {exc}")
                    continue
                for row in rows:
                    local_type = int(row[2] or 0)
                    base_type = local_type & 0xFFFF
                    if base_type == _TYPE_SYSTEM:
                        read_stats.skipped_system += 1
                        continue
                    if text_only and base_type != _TYPE_TEXT:
                        read_stats.skipped_non_text += 1
                        continue
                    create_time = int(row[4] or 0)
                    if cutoff_ts is not None and create_time < cutoff_ts:
                        read_stats.skipped_time += 1
                        continue
                    compress_type = row[6]
                    content = _decode_message_content(row[5], compress_type)
                    if content is None:
                        read_stats.skipped_decompress += 1
                        continue
                    sender = _resolve_sender(
                        contacts,
                        name2id,
                        row[3],
                        content,
                        is_group,
                        self_wxid=self_wxid,
                        self_display_name=self_display_name,
                        chat_partner=chat_title,
                    )
                    if is_group:
                        _, content = _parse_group_sender(content)
                    body = content.strip()
                    if text_only:
                        if not is_plain_text_content(body):
                            read_stats.skipped_non_text += 1
                            continue
                    else:
                        label = _type_label(local_type)
                        body = label if label and not body else body
                        if label and content.strip():
                            body = f"{label}\n{content.strip()}"
                    if not body:
                        read_stats.skipped_empty += 1
                        continue
                    dt = datetime.fromtimestamp(create_time, tz=timezone.utc).astimezone(tz)
                    iso_date = dt.isoformat()
                    server_id = str(row[1] or row[0] or "")
                    msg_id = stable_hash(chat_id, server_id, str(row[0]), body[:120])
                    messages.append(
                        RawMessage(
                            source="wechat",
                            source_id=chat_id,
                            message_id=msg_id,
                            date=iso_date,
                            text=body,
                            link=f"wechat-local:{username}/{server_id}",
                            sender=sender,
                            chat_title=chat_title,
                            has_media=base_type in _MEDIA_TYPES,
                        )
                    )
                    read_stats.messages += 1
        finally:
            conn.close()

    messages.sort(key=lambda m: m.date)
    return messages
