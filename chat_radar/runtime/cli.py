"""CLI 参数解析."""

from __future__ import annotations

import argparse
import sys

from chat_radar import __version__
from chat_radar.runtime.runner import dispatch


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="chat_radar",
        description="CHAT-RADAR — Telegram / 微信 招聘信息个人雷达",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = p.add_subparsers(dest="command", metavar="command")

    sub.add_parser("auth", help="交互登录 Telegram")
    sub.add_parser("status", help="运行状态概览")

    fetch_p = sub.add_parser("fetch", help="增量拉取 Telegram 频道")
    fetch_p.add_argument("--channel", help="仅拉取指定频道 @username")
    fetch_p.add_argument("--fix", action="store_true", help="未登录时引导完成登录")

    digest_p = sub.add_parser("digest", help="fetch + filter + 生成 digest（含微信）")
    digest_p.add_argument("--since", type=int, default=24, help="回溯小时数（默认 24）")
    digest_p.add_argument("--skip-fetch", action="store_true", help="跳过 Telegram 拉取")
    digest_p.add_argument(
        "--skip-wechat-inbox",
        action="store_true",
        help="跳过微信 inbox 扫描（wechat.enabled 时默认会先扫描）",
    )
    digest_p.add_argument(
        "--skip-wechat-export",
        action="store_true",
        help="跳过微信 export 目录导入",
    )
    digest_p.add_argument(
        "--skip-wechat-sync",
        action="store_true",
        help="跳过微信本地库 sync（macOS + 密钥可用时默认会先同步）",
    )
    digest_p.add_argument("--fix", action="store_true", help="未登录时引导完成登录")

    preflight_p = sub.add_parser("preflight", help="检查 fetch/digest 前置条件")
    preflight_p.add_argument("action", nargs="?", default="fetch", choices=("fetch", "digest"))
    preflight_p.add_argument("--fix", action="store_true", help="未登录时引导完成登录")

    setup_p = sub.add_parser("setup", help="引导式首次配置")
    setup_p.add_argument("--force", action="store_true", help="重新配置已有项")

    channels_p = sub.add_parser("channels", help="频道管理")
    channels_p.add_argument(
        "action",
        nargs="?",
        default="list",
        choices=("list", "add", "remove", "enable", "disable"),
        help="list | add | remove | enable | disable",
    )
    channels_p.add_argument("ref", nargs="?", help="频道 @username（add/remove/enable/disable）")
    channels_p.add_argument("--note", default="", help="add 时的备注")
    channels_p.add_argument("--disabled", action="store_true", help="add 时默认禁用")

    for name in ("help", "config", "selftest", "version"):
        sub.add_parser(name, help=f"运行 {name}")

    wechat = sub.add_parser("wechat", help="微信 ingest / digest")
    wechat_sub = wechat.add_subparsers(dest="wechat_cmd", metavar="wechat-command")

    wp = wechat_sub.add_parser("parse", help="解析微信 PC 导出 TXT")
    wp.add_argument("file", help="导出文件路径")
    wp.add_argument("--chat", help="群名称（默认取文件名）")

    wechat_sub.add_parser("inbox", help="扫描 data/wechat_inbox 手动落盘文件")
    wechat_sub.add_parser("import", help="扫描 data/wechat_exports 未处理的 PC 导出 TXT")
    wechat_sub.add_parser("locate", help="探测 macOS 微信本地数据目录")
    wechat_sub.add_parser("status", help="微信模块健康检查")
    wkeys = wechat_sub.add_parser("keys", help="密钥管理")
    wkeys_sub = wkeys.add_subparsers(dest="wechat_keys_cmd", metavar="keys-command")
    wkeys_sub.add_parser("derive", help="从已保存 passphrase 派生密钥（多账号自动匹配）")
    wkeys_sub.add_parser("validate", help="校验密钥文件与当前账号是否匹配")
    ws = wechat_sub.add_parser("sync", help="解密本地微信库并导入消息（macOS）")
    ws.add_argument("--since", type=int, default=24, help="回溯小时数（默认 24；0=全量）")
    ws.add_argument("--scope", choices=("groups", "private", "all"), help="同步范围（默认 groups）")
    wsum = wechat_sub.add_parser("summary", help="按联系人生成聊天记录 Markdown 摘要")
    wsum.add_argument("--since", type=int, default=24, help="回溯小时数（默认 24；0=全量）")
    wsum.add_argument("--scope", choices=("groups", "private", "all"), help="摘要范围（默认 all）")
    wsum.add_argument("--from-db", action="store_true", help="直接从本地解密库读取（不依赖 JSONL）")
    wsum.add_argument("--person", help="仅生成指定联系人")
    wsum.add_argument("--output", help="输出目录（默认 reports/wechat_contacts）")
    wd = wechat_sub.add_parser("digest", help="对已入库微信消息生成 digest")
    wd.add_argument("--since", type=int, default=24, help="回溯小时数（默认 24）")

    return p


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print(build_parser().format_help())
        sys.exit(0)
    if args[0] in ("-h", "--help"):
        print(build_parser().format_help())
        sys.exit(0)
    if args[0] == "--version":
        print(__version__)
        sys.exit(0)
    code = dispatch(args)
    if code == 0 and args[0] == "help":
        print(build_parser().format_help())
    sys.exit(code)


if __name__ == "__main__":
    main()
