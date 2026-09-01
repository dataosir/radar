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

    for name in ("help", "auth", "fetch", "digest", "channels", "status", "config", "selftest", "version"):
        sub.add_parser(name, help=f"运行 {name}")

    wechat = sub.add_parser("wechat", help="微信 ingest / digest")
    wechat_sub = wechat.add_subparsers(dest="wechat_cmd", metavar="wechat-command")

    wp = wechat_sub.add_parser("parse", help="解析微信 PC 导出 TXT")
    wp.add_argument("file", help="导出文件路径")
    wp.add_argument("--chat", help="群名称（默认取文件名）")

    wechat_sub.add_parser("inbox", help="扫描 data/wechat_inbox 手动落盘文件")
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
