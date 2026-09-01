"""命令编排."""

from __future__ import annotations

import sys
from datetime import datetime, timezone

from tg_radar import __version__
from tg_radar.config import load_config
from tg_radar.core.paths import logs_dir
from tg_radar.core.utils import setup_logging
from tg_radar.selftest import run_selftest


def run_digest(cfg) -> int:
    api_id = cfg.get("telegram.api_id", 0)
    if not api_id or api_id == 0:
        print("错误：请先在 tg_radar_config.json 配置 telegram.api_id / api_hash", file=sys.stderr)
        return 1
    print("digest：Telethon ingest 尚未实现（见 docs/prd/05-roadmap-backlog.md P0-04）", file=sys.stderr)
    return 1


def run_auth(cfg) -> int:
    print("auth：Telethon 登录尚未实现（下一步 P0-04）", file=sys.stderr)
    return 1


def run_status(cfg) -> int:
    print(f"TG-RADAR v{__version__} | 配置: 已加载")
    print("ingest 未实现，暂无统计数据。")
    return 0


def bootstrap() -> tuple:
    cfg = load_config()
    log_level = cfg.get("log.level", "INFO")
    logger = setup_logging(logs_dir() / "tg_radar.log", level=log_level)
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

    print(f"未知命令: {cmd}", file=sys.stderr)
    return 1
