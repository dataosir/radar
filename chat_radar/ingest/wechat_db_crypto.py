"""macOS 微信 SQLCipher 4 数据库解密（CommonCrypto，零 pip 依赖）."""

from __future__ import annotations

import ctypes
import ctypes.util
import hashlib
import hmac as hmac_mod
import json
import platform
import shutil
import struct
from dataclasses import dataclass, field
from pathlib import Path

PAGE_SZ = 4096
KEY_SZ = 32
SALT_SZ = 16
IV_SZ = 16
HMAC_SZ = 64
RESERVE_SZ = 80
SQLITE_HDR = b"SQLite format 3\x00"

_kCCDecrypt = 1
_kCCAlgorithmAES = 0


class WeChatCryptoError(RuntimeError):
    """解密或密钥校验失败."""


@dataclass
class DecryptStats:
    """解密过程统计."""

    decrypted: list[Path] = field(default_factory=list)
    cached: list[Path] = field(default_factory=list)
    skipped_no_key: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    @property
    def total_ok(self) -> int:
        return len(self.decrypted) + len(self.cached)


def load_keys_file_raw(path: Path) -> dict:
    """加载完整密钥 JSON（含 _wxid / _db_dir 元数据）."""
    if not path.is_file():
        raise WeChatCryptoError(f"密钥文件不存在: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise WeChatCryptoError("密钥文件格式错误：应为 JSON 对象")
    return data


def load_keys_file(path: Path) -> dict:
    """加载 wcdb-key-tool 格式的密钥 JSON（仅密钥条目）."""
    data = load_keys_file_raw(path)
    return {k: v for k, v in data.items() if not str(k).startswith("_")}


def _require_macos() -> None:
    if platform.system() != "Darwin":
        raise WeChatCryptoError("微信本地库解密仅支持 macOS（CommonCrypto）")


def _load_cccrypt():
    lib = ctypes.CDLL(ctypes.util.find_library("System"))
    lib.CCCrypt.argtypes = [
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_char_p,
        ctypes.c_size_t,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_size_t,
        ctypes.c_char_p,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    lib.CCCrypt.restype = ctypes.c_int32
    return lib


def aes_cbc_decrypt(key: bytes, iv: bytes, data: bytes) -> bytes:
    """AES-256-CBC 解密（SQLCipher 页面，无 PKCS padding）."""
    _require_macos()
    lib = _load_cccrypt()
    out_buf = ctypes.create_string_buffer(len(data) + 32)
    out_len = ctypes.c_size_t(0)
    status = lib.CCCrypt(
        _kCCDecrypt,
        _kCCAlgorithmAES,
        0,
        key,
        len(key),
        iv,
        data,
        len(data),
        out_buf,
        len(out_buf),
        ctypes.byref(out_len),
    )
    if status != 0:
        raise WeChatCryptoError(f"CCCrypt 解密失败: status={status}")
    return out_buf.raw[: out_len.value]


def verify_enc_key(enc_key: bytes, db_page1: bytes) -> bool:
    """HMAC-SHA512 校验 page 1，确认密钥正确."""
    if len(db_page1) < PAGE_SZ:
        return False
    salt = db_page1[:SALT_SZ]
    mac_salt = bytes(b ^ 0x3A for b in salt)
    mac_key = hashlib.pbkdf2_hmac("sha512", enc_key, mac_salt, 2, dklen=KEY_SZ)
    hmac_data = db_page1[SALT_SZ : PAGE_SZ - RESERVE_SZ + IV_SZ]
    stored_hmac = db_page1[PAGE_SZ - HMAC_SZ : PAGE_SZ]
    hm = hmac_mod.new(mac_key, hmac_data, hashlib.sha512)
    hm.update(struct.pack("<I", 1))
    return hm.digest() == stored_hmac


def _decrypt_page(enc_key: bytes, page_data: bytes, pgno: int) -> bytes:
    iv = page_data[PAGE_SZ - RESERVE_SZ : PAGE_SZ - RESERVE_SZ + IV_SZ]
    if pgno == 1:
        encrypted = page_data[SALT_SZ : PAGE_SZ - RESERVE_SZ]
        decrypted = aes_cbc_decrypt(enc_key, iv, encrypted)
        return bytes(SQLITE_HDR + decrypted + b"\x00" * RESERVE_SZ)
    encrypted = page_data[: PAGE_SZ - RESERVE_SZ]
    decrypted = aes_cbc_decrypt(enc_key, iv, encrypted)
    return decrypted + b"\x00" * RESERVE_SZ


def decrypt_database(src: Path, dst: Path, enc_key: bytes) -> None:
    """将单个加密 .db 解密为明文 SQLite 文件."""
    _require_macos()
    file_size = src.stat().st_size
    if file_size < PAGE_SZ:
        raise WeChatCryptoError(f"数据库过小: {src}")

    with src.open("rb") as fin:
        page1 = fin.read(PAGE_SZ)
        if not verify_enc_key(enc_key, page1):
            raise WeChatCryptoError(f"密钥校验失败: {src.name}")

        total_pages = file_size // PAGE_SZ
        if file_size % PAGE_SZ != 0:
            total_pages += 1

        dst.parent.mkdir(parents=True, exist_ok=True)
        with dst.open("wb") as fout:
            fin.seek(0)
            for pgno in range(1, total_pages + 1):
                page = fin.read(PAGE_SZ)
                if len(page) < PAGE_SZ:
                    if not page:
                        break
                    page = page + b"\x00" * (PAGE_SZ - len(page))
                fout.write(_decrypt_page(enc_key, page, pgno))


def _key_path_variants(rel_path: str) -> list[str]:
    normalized = rel_path.replace("\\", "/")
    variants: list[str] = []
    for candidate in (rel_path, normalized, normalized.replace("/", "\\")):
        if candidate not in variants:
            variants.append(candidate)
    return variants


def _get_key_info(keys: dict, rel_path: str) -> dict | None:
    if ".." in rel_path.replace("\\", "/").split("/"):
        return None
    for candidate in _key_path_variants(rel_path):
        info = keys.get(candidate)
        if isinstance(info, dict) and info.get("enc_key"):
            return info
    return None


def decrypt_tree(
    db_storage: Path,
    out_dir: Path,
    keys: dict,
    *,
    only_prefixes: tuple[str, ...] = ("message/message_", "contact/", "session/"),
    stats: DecryptStats | None = None,
) -> list[Path]:
    """解密 db_storage 下匹配前缀的数据库，返回已解密的文件路径."""
    _require_macos()
    if shutil.which("sqlite3") is None:
        raise WeChatCryptoError("未找到 sqlite3，请安装 Xcode Command Line Tools")

    result = stats if stats is not None else DecryptStats()
    decrypted: list[Path] = []

    for src in sorted(db_storage.rglob("*.db")):
        if src.name.endswith(("-wal", "-shm")):
            continue
        rel = src.relative_to(db_storage).as_posix()
        if only_prefixes and not any(rel.startswith(p) for p in only_prefixes):
            continue
        key_info = _get_key_info(keys, rel)
        if not key_info:
            result.skipped_no_key.append(rel)
            continue
        enc_key = bytes.fromhex(str(key_info["enc_key"]))
        dst = out_dir / rel
        if dst.is_file() and dst.stat().st_mtime >= src.stat().st_mtime:
            result.cached.append(dst)
            decrypted.append(dst)
            continue
        try:
            decrypt_database(src, dst, enc_key)
            result.decrypted.append(dst)
            decrypted.append(dst)
        except WeChatCryptoError as exc:
            result.failed.append(f"{rel}: {exc}")

    return decrypted
