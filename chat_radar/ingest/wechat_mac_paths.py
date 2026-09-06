"""macOS 微信本地数据目录自动发现."""

from __future__ import annotations

import platform
import re
from dataclasses import dataclass
from pathlib import Path

SQLITE_MAGIC = b"SQLite format 3\x00"
_WXID_RE = re.compile(r"^wxid_[a-zA-Z0-9_]+$")

# 微信 4.x macOS 沙盒路径（优先）
MAC_SANDBOX_ROOT = (
    Path.home() / "Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files"
)
# 旧版 / 部分迁移场景
MAC_LEGACY_ROOT = Path.home() / "Documents/xwechat_files"


@dataclass(frozen=True)
class WeChatMacAccount:
    """单个微信账号的本地数据根."""

    wxid: str
    root: Path
    db_storage: Path

    @property
    def message_dir(self) -> Path:
        return self.db_storage / "message"

    @property
    def contact_db(self) -> Path:
        return self.db_storage / "contact" / "contact.db"

    @property
    def session_db(self) -> Path:
        return self.db_storage / "session" / "session.db"

    def message_dbs(self) -> list[Path]:
        msg_dir = self.message_dir
        if not msg_dir.is_dir():
            return []
        return sorted(
            p
            for p in msg_dir.glob("message_*.db")
            if p.is_file() and not p.name.endswith(("-wal", "-shm"))
        )


@dataclass(frozen=True)
class WeChatMacDiscovery:
    """一次发现结果."""

    accounts: list[WeChatMacAccount]
    wechat_version: str | None
    searched_roots: list[Path]


def _is_macos() -> bool:
    return platform.system() == "Darwin"


def _read_wechat_version() -> str | None:
    info = Path("/Applications/WeChat.app/Contents/Info.plist")
    if not info.exists():
        return None
    try:
        import plistlib

        data = plistlib.loads(info.read_bytes())
        ver = data.get("CFBundleShortVersionString")
        return str(ver) if ver else None
    except (OSError, ValueError, plistlib.InvalidFileException):
        return None


def _is_encrypted_db(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 16:
        return False
    head = path.read_bytes()[:16]
    return head != SQLITE_MAGIC


def _scan_root(root: Path) -> list[WeChatMacAccount]:
    if not root.is_dir():
        return []
    accounts: list[WeChatMacAccount] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or not _WXID_RE.match(entry.name):
            continue
        db_storage = entry / "db_storage"
        if db_storage.is_dir():
            accounts.append(WeChatMacAccount(wxid=entry.name, root=entry, db_storage=db_storage))
    return accounts


def discover_mac_wechat() -> WeChatMacDiscovery:
    """扫描本机 macOS 微信数据目录，返回已登录账号列表."""
    if not _is_macos():
        return WeChatMacDiscovery(accounts=[], wechat_version=None, searched_roots=[])

    roots: list[Path] = []
    for candidate in (MAC_SANDBOX_ROOT, MAC_LEGACY_ROOT):
        if candidate.is_dir():
            roots.append(candidate)

    accounts: list[WeChatMacAccount] = []
    seen_wxids: set[str] = set()
    for root in roots:
        for acct in _scan_root(root):
            if acct.wxid not in seen_wxids:
                seen_wxids.add(acct.wxid)
                accounts.append(acct)

    return WeChatMacDiscovery(
        accounts=accounts,
        wechat_version=_read_wechat_version(),
        searched_roots=roots,
    )


def account_last_activity(acct: WeChatMacAccount) -> float:
    """账号 db_storage 下最近文件修改时间（用于判断当前登录账号）."""
    latest = 0.0
    db_storage = acct.db_storage
    if not db_storage.is_dir():
        return latest
    for path in db_storage.rglob("*.db"):
        if path.name.endswith(("-wal", "-shm")):
            continue
        try:
            latest = max(latest, path.stat().st_mtime)
        except OSError:
            continue
    return latest


def pick_active_account(discovery: WeChatMacDiscovery) -> WeChatMacAccount | None:
    """取最近有数据库写入的账号（多账号时判断当前登录账号）."""
    if not discovery.accounts:
        return None
    if len(discovery.accounts) == 1:
        return discovery.accounts[0]
    return max(discovery.accounts, key=account_last_activity)


def pick_primary_account(discovery: WeChatMacDiscovery) -> WeChatMacAccount | None:
    """取主账号：优先最近活跃，其次消息库最大."""
    if not discovery.accounts:
        return None
    if len(discovery.accounts) == 1:
        return discovery.accounts[0]

    active = pick_active_account(discovery)
    if active is None:
        return None

    # 若多个账号活跃度接近（5 分钟内），回退到消息库体积
    activities = [(account_last_activity(a), a) for a in discovery.accounts]
    activities.sort(reverse=True)
    if len(activities) >= 2 and activities[0][0] - activities[1][0] < 300:
        def _size(acct: WeChatMacAccount) -> int:
            return sum(p.stat().st_size for p in acct.message_dbs() if p.is_file())
        return max(discovery.accounts, key=_size)
    return active


def summarize_account(acct: WeChatMacAccount) -> dict[str, object]:
    """生成人类可读的账号摘要（供 locate 输出）."""
    from datetime import datetime, timezone

    msg_dbs = acct.message_dbs()
    encrypted = 0
    for db in msg_dbs[:3]:
        if _is_encrypted_db(db):
            encrypted += 1
    last_ts = account_last_activity(acct)
    last_active = (
        datetime.fromtimestamp(last_ts, tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
        if last_ts > 0
        else "未知"
    )
    return {
        "wxid": acct.wxid,
        "db_storage": str(acct.db_storage),
        "message_db_count": len(msg_dbs),
        "sample_encrypted": encrypted > 0,
        "contact_db": str(acct.contact_db),
        "session_db": str(acct.session_db),
        "last_active": last_active,
    }
