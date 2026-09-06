"""微信 SQLCipher 密钥派生（多账号自动匹配）."""

from __future__ import annotations

import hashlib
import hmac as hmac_mod
import json
import struct
from dataclasses import dataclass, field
from pathlib import Path

from chat_radar.ingest.wechat_mac_paths import (
    WeChatMacAccount,
    WeChatMacDiscovery,
    discover_mac_wechat,
    pick_active_account,
)

PAGE_SZ = 4096
KEY_SZ = 32
SALT_SZ = 16
RESERVE_SZ = 80
HMAC_SZ = 64

PASSPHRASE_FILE = Path.home() / ".wcdb-key-tool" / "wechat-passphrase.json"


@dataclass
class KeysInspection:
    """密钥文件健康检查结果."""

    keys_path: Path
    exists: bool
    wxid: str | None = None
    db_dir: str | None = None
    key_count: int = 0
    total_dbs: int = 0
    coverage_ratio: float = 0.0
    account_match: bool = False
    active_account: str | None = None
    issues: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        pass

    @property
    def ok(self) -> bool:
        return self.exists and self.key_count > 0 and not self.issues


def inspect_keys_file(
    keys_path: Path,
    account: WeChatMacAccount | None = None,
) -> KeysInspection:
    """检查密钥文件是否与当前账号匹配、覆盖率是否足够."""
    discovery = discover_mac_wechat()
    active = pick_active_account(discovery)
    result = KeysInspection(
        keys_path=keys_path,
        exists=keys_path.is_file(),
        active_account=active.wxid if active else None,
    )
    if not result.exists:
        result.issues.append("密钥文件不存在")
        return result

    try:
        raw = json.loads(keys_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        result.issues.append(f"密钥文件无法解析: {exc}")
        return result

    if not isinstance(raw, dict):
        result.issues.append("密钥文件格式错误")
        return result

    result.wxid = str(raw.get("_wxid") or "") or None
    result.db_dir = str(raw.get("_db_dir") or "") or None
    result.key_count = sum(
        1 for k, v in raw.items() if not str(k).startswith("_") and isinstance(v, dict) and v.get("enc_key")
    )

    acct = account
    if acct is None and result.db_dir:
        for candidate in discovery.accounts:
            if str(candidate.db_storage) == result.db_dir:
                acct = candidate
                break
    if acct is None:
        acct = active

    if acct is not None:
        db_files = collect_db_files(acct.db_storage)
        result.total_dbs = len(db_files)
        salts = {s for _, _, _, s, _ in db_files}
        if salts:
            result.coverage_ratio = result.key_count / len(salts)
        result.account_match = result.wxid == acct.wxid if result.wxid else True
        if result.wxid and result.wxid != acct.wxid:
            result.issues.append(
                f"密钥账号 {result.wxid} 与目标账号 {acct.wxid} 不一致，请重新 derive"
            )
        if result.coverage_ratio < 0.5 and result.total_dbs > 0:
            result.issues.append(
                f"密钥覆盖率偏低 ({result.key_count}/{len(salts)} salts)，部分库可能无法解密"
            )

    if result.key_count == 0:
        result.issues.append("密钥文件无有效 enc_key 条目")

    return result


def verify_enc_key(enc_key: bytes, db_page1: bytes) -> bool:
    """HMAC-SHA512 校验 page 1，确认密钥正确."""
    if len(db_page1) < PAGE_SZ:
        return False
    salt = db_page1[:SALT_SZ]
    mac_salt = bytes(b ^ 0x3A for b in salt)
    mac_key = hashlib.pbkdf2_hmac("sha512", enc_key, mac_salt, 2, dklen=KEY_SZ)
    hmac_data = db_page1[SALT_SZ : PAGE_SZ - RESERVE_SZ + 16]
    stored_hmac = db_page1[PAGE_SZ - HMAC_SZ : PAGE_SZ]
    hm = hmac_mod.new(mac_key, hmac_data, hashlib.sha512)
    hm.update(struct.pack("<I", 1))
    return hm.digest() == stored_hmac


def collect_db_files(db_storage: Path) -> list[tuple[str, Path, int, str, bytes]]:
    """收集 db_storage 下所有 .db 文件及 salt."""
    db_files: list[tuple[str, Path, int, str, bytes]] = []
    for path in sorted(db_storage.rglob("*.db")):
        if path.name.endswith(("-wal", "-shm")):
            continue
        size = path.stat().st_size
        if size < PAGE_SZ:
            continue
        page1 = path.read_bytes()[:PAGE_SZ]
        rel = path.relative_to(db_storage).as_posix()
        salt = page1[:SALT_SZ].hex()
        db_files.append((rel, path, size, salt, page1))
    return db_files


def derive_keys_from_passphrase(
    passphrase: bytes,
    db_storage: Path,
    *,
    iterations: int = 256000,
) -> dict[str, str]:
    """用 passphrase + PBKDF2 派生 enc_key，返回 salt_hex -> enc_key_hex."""
    db_files = collect_db_files(db_storage)
    salt_to_dbs: dict[str, list[str]] = {}
    for rel, _path, _sz, salt, _page1 in db_files:
        salt_to_dbs.setdefault(salt, []).append(rel)

    key_map: dict[str, str] = {}
    for salt_hex in salt_to_dbs:
        salt = bytes.fromhex(salt_hex)
        enc_key = hashlib.pbkdf2_hmac("sha512", passphrase, salt, iterations, dklen=KEY_SZ)
        for rel, _path, _sz, s, page1 in db_files:
            if s == salt_hex and verify_enc_key(enc_key, page1):
                key_map[salt_hex] = enc_key.hex()
                break
    return key_map


def build_keys_json(
    account: WeChatMacAccount,
    key_map: dict[str, str],
    db_files: list[tuple[str, Path, int, str, bytes]],
) -> dict:
    """构建 wcdb-key-tool 兼容的密钥 JSON."""
    result: dict = {}
    for rel, _path, sz, salt_hex, _page1 in db_files:
        if salt_hex in key_map:
            result[rel] = {
                "enc_key": key_map[salt_hex],
                "salt": salt_hex,
                "size_mb": round(sz / 1024 / 1024, 1),
            }
    result["_db_dir"] = str(account.db_storage)
    result["_wxid"] = account.wxid
    return result


def find_account_for_passphrase(
    passphrase_hex: str,
    discovery: WeChatMacDiscovery | None = None,
) -> tuple[WeChatMacAccount, dict[str, str]] | None:
    """遍历所有账号，找到 passphrase 能解密的账号."""
    disc = discovery or discover_mac_wechat()
    passphrase = bytes.fromhex(passphrase_hex)
    for acct in disc.accounts:
        key_map = derive_keys_from_passphrase(passphrase, acct.db_storage)
        if key_map:
            return acct, key_map
    return None


def load_saved_passphrase() -> str | None:
    """加载 wcdb-key-tool 保存的 passphrase."""
    if not PASSPHRASE_FILE.is_file():
        return None
    try:
        data = json.loads(PASSPHRASE_FILE.read_text(encoding="utf-8"))
        ph = data.get("passphrase")
        return str(ph) if ph else None
    except (OSError, json.JSONDecodeError, TypeError):
        return None


def derive_and_save_keys(
    output: Path,
    *,
    db_storage: Path | None = None,
    passphrase_hex: str | None = None,
) -> tuple[WeChatMacAccount, int, int]:
    """从 passphrase 派生密钥并写入 JSON。返回 (账号, 成功数, 总数)."""
    ph = passphrase_hex or load_saved_passphrase()
    if not ph:
        raise FileNotFoundError(
            f"未找到 passphrase，请先运行密钥提取或确认 {PASSPHRASE_FILE} 存在"
        )

    discovery = discover_mac_wechat()
    if db_storage is not None:
        # 指定目录时先尝试该账号，失败再遍历
        for acct in discovery.accounts:
            if acct.db_storage == db_storage or acct.db_storage.resolve() == db_storage.resolve():
                key_map = derive_keys_from_passphrase(bytes.fromhex(ph), acct.db_storage)
                if key_map:
                    db_files = collect_db_files(acct.db_storage)
                    result = build_keys_json(acct, key_map, db_files)
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
                    return acct, len(key_map), len({s for _, _, _, s, _ in db_files})

    match = find_account_for_passphrase(ph, discovery)
    if match is None:
        active = pick_active_account(discovery)
        hint = f"最近活跃账号: {active.wxid}" if active else "无"
        raise ValueError(
            f"passphrase 无法解密任何账号的数据库（{hint}）。"
            "可能原因：捕获时登录的账号与目标目录不一致，需重新捕获 passphrase。"
        )

    acct, key_map = match
    db_files = collect_db_files(acct.db_storage)
    result = build_keys_json(acct, key_map, db_files)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return acct, len(key_map), len({s for _, _, _, s, _ in db_files})
