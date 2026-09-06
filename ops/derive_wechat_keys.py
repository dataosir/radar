#!/usr/bin/env python3
"""从已保存 passphrase 派生微信密钥（可 sudo 独立运行，无 telethon 依赖）."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chat_radar.ingest.wechat_keys import derive_and_save_keys, load_saved_passphrase  # noqa: E402


def main() -> int:
    keys_out = ROOT / "data" / "wechat_keys.json"
    passphrase = load_saved_passphrase()
    if not passphrase:
        print(
            f"错误：未找到 passphrase（{Path.home()}/.wcdb-key-tool/wechat-passphrase.json）",
            file=sys.stderr,
        )
        print("请先运行 ./ops/extract_wechat_keys.sh 完成 LLDB 捕获", file=sys.stderr)
        return 1

    print("从已保存 passphrase 派生密钥（自动匹配账号）...")
    try:
        account, ok_count, total_salts = derive_and_save_keys(keys_out)
    except (FileNotFoundError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    keys_out.chmod(0o600)
    print(f"完成: {keys_out}")
    print(f"  账号: {account.wxid}")
    print(f"  密钥: {ok_count}/{total_salts} salts 验证通过")
    print(f"  db_storage: {account.db_storage}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
