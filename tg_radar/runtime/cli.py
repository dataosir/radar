"""CLI 参数解析."""

from __future__ import annotations

import argparse
import sys

from tg_radar import __version__
from tg_radar.runtime.runner import dispatch


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tg_radar",
        description="TG-RADAR — Telegram 招聘信息个人雷达",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument(
        "command",
        nargs="?",
        default="help",
        choices=["help", "auth", "fetch", "digest", "channels", "status", "config", "selftest", "version"],
        help="子命令",
    )
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
