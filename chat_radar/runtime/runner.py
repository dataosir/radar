"""命令编排."""

from __future__ import annotations

import sys

from chat_radar import __version__
from chat_radar.config import load_config
from chat_radar.core.paths import logs_dir
from chat_radar.core.utils import setup_logging
from chat_radar.runtime.wechat_runner import (
    run_wechat_digest,
    run_wechat_inbox,
    run_wechat_parse,
)
from chat_radar.selftest import run_selftest


def run_digest(cfg) -> int:
    api_id = cfg.get("telegram.api_id", 0)
    if not api_id or api_id == 0:
        print("错误：请先在 chat_radar_config.json 配置 telegram.api_id / api_hash", file=sys.stderr)
        return 1
    print("digest：Telethon ingest 尚未实现（见 docs/prd/05-roadmap-backlog.md P0-04）", file=sys.stderr)
    return 1


def run_auth(cfg) -> int:
    print("auth：Telethon 登录尚未实现（下一步 P0-04）", file=sys.stderr)
    return 1


def run_status(cfg) -> int:
    wechat_on = "开启" if cfg.get("wechat.enabled", False) else "关闭"
    print(f"CHAT-RADAR v{__version__} | 配置: 已加载 | 微信: {wechat_on}")
    print("Telegram ingest 未实现，暂无统计数据。")
    return 0


def bootstrap() -> tuple:
    cfg = load_config()
    log_level = cfg.get("log.level", "INFO")
    logger = setup_logging(logs_dir() / "chat_radar.log", level=log_level)
    return cfg, logger


def dispatch(argv: list[str]) -> int:
    cfg, _logger = bootstrap()
    cmd = argv[0] if argv else "help"

    if cmd in ("-h", "--help", "help"):
        return 0
    if cmd == "selftest":
        return run_selftest()
    if cmd == "digest":
        return run_digest(cfg)
    if cmd == "auth":
        return run_auth(cfg)
    if cmd == "status":
        return run_status(cfg)
    if cmd == "version":
        print(__version__)
        return 0
    if cmd == "wechat":
        return _dispatch_wechat(cfg, argv[1:])
    print(f"未知命令: {cmd}", file=sys.stderr)
    return 1


def _dispatch_wechat(cfg, args: list[str]) -> int:
    if not args or args[0] in ("-h", "--help"):
        print("用法: chat_radar wechat parse <file> [--chat 群名] | inbox | digest [--since 24]")
        return 0
    sub = args[0]
    if sub == "parse":
        if len(args) < 2:
            print("错误: 需要文件路径", file=sys.stderr)
            return 1
        chat = None
        if "--chat" in args:
            idx = args.index("--chat")
            if idx + 1 < len(args):
                chat = args[idx + 1]
        return run_wechat_parse(cfg, args[1], chat_title=chat)
    if sub == "inbox":
        return run_wechat_inbox(cfg)
    if sub == "digest":
        since = 24
        if "--since" in args:
            idx = args.index("--since")
            if idx + 1 < len(args):
                try:
                    since = int(args[idx + 1])
                except ValueError:
                    print("错误: --since 需要整数", file=sys.stderr)
                    return 1
        return run_wechat_digest(cfg, since_hours=since)
    print(f"未知 wechat 子命令: {sub}", file=sys.stderr)
    return 1
