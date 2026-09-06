"""命令编排."""

from __future__ import annotations

import sys

from chat_radar import __version__
from chat_radar.config import load_config
from chat_radar.core.paths import data_dir, logs_dir
from chat_radar.core.interaction_log import log_interaction
from chat_radar.core.utils import setup_logging
from chat_radar.runtime.setup_wizard import run_config_status, run_setup
from chat_radar.runtime.tg_runner import (
    _enabled_channels,
    _session_exists,
    _telegram_configured,
    check_telegram_login,
    run_auth,
    run_channels_add,
    run_channels_enable,
    run_channels_list,
    run_channels_remove,
    run_digest,
    run_fetch,
    run_preflight,
)
from chat_radar.runtime.wechat_runner import (
    format_wechat_status_lines,
    run_wechat_digest,
    run_wechat_import_exports,
    run_wechat_inbox,
    run_wechat_keys_derive,
    run_wechat_keys_validate,
    run_wechat_locate,
    run_wechat_parse,
    run_wechat_status,
    run_wechat_summary,
    run_wechat_sync,
)
from chat_radar.selftest import run_selftest


def run_status(cfg) -> int:
    wechat_on = "开启" if cfg.get("wechat.enabled", False) else "关闭"
    tg_channels = sum(
        1 for c in (cfg.raw().get("channels") or []) if isinstance(c, dict) and c.get("enabled")
    )
    print(f"CHAT-RADAR v{__version__} | 配置: 已加载 | 微信: {wechat_on} | TG 启用频道: {tg_channels}")

    if _telegram_configured(cfg) is None:
        print("Telegram: 未配置 API（运行 ./start.sh setup）")
    elif not _session_exists(cfg):
        print("Telegram: 已配置 API，尚未登录（运行 ./start.sh auth）")
    else:
        logged_in, detail = check_telegram_login(cfg)
        print(f"Telegram: {detail}" if logged_in else f"Telegram: {detail}（请运行 ./start.sh auth）")

    raw = data_dir() / "raw_messages.jsonl"
    if raw.exists():
        lines = sum(1 for _ in raw.open(encoding="utf-8"))
        print(f"raw_messages.jsonl: {lines} 行")
    else:
        print("raw_messages.jsonl: 尚无数据")

    for line in format_wechat_status_lines(cfg):
        print(line)
    return 0


def bootstrap() -> tuple:
    cfg = load_config()
    log_level = cfg.get("log.level", "INFO")
    logger = setup_logging(logs_dir() / "chat_radar.log", level=log_level)
    return cfg, logger


def _parse_since(args: list[str], default: int = 24) -> int | tuple[int, str]:
    if "--since" not in args:
        return default
    idx = args.index("--since")
    if idx + 1 >= len(args):
        return default, "错误: --since 需要整数"
    try:
        return int(args[idx + 1])
    except ValueError:
        return default, "错误: --since 需要整数"


def _parse_channel(args: list[str]) -> str | None:
    if "--channel" not in args:
        return None
    idx = args.index("--channel")
    if idx + 1 >= len(args):
        return None
    return args[idx + 1]


def _parse_skip_fetch(args: list[str]) -> bool:
    return "--skip-fetch" in args


def _parse_skip_wechat_inbox(args: list[str]) -> bool:
    return "--skip-wechat-inbox" in args


def _parse_skip_wechat_export(args: list[str]) -> bool:
    return "--skip-wechat-export" in args


def _parse_skip_wechat_sync(args: list[str]) -> bool:
    return "--skip-wechat-sync" in args


def _parse_fix(args: list[str]) -> bool:
    return "--fix" in args


def dispatch(argv: list[str]) -> int:
    import time

    cfg, _logger = bootstrap()
    cmd = argv[0] if argv else "help"
    rest = argv[1:]

    if cmd in ("-h", "--help", "help"):
        return 0

    started = time.monotonic()
    log_interaction("command.start", command=cmd, args=" ".join(rest) if rest else None)
    code = _dispatch_command(cfg, cmd, rest)
    duration_ms = int((time.monotonic() - started) * 1000)
    log_interaction(
        "command.done",
        command=cmd,
        exit_code=code,
        duration_ms=duration_ms,
        status="ok" if code == 0 else "error",
        level="info" if code == 0 else "error",
    )
    return code


def _dispatch_command(cfg, cmd: str, rest: list[str]) -> int:
    if cmd == "selftest":
        return run_selftest()
    if cmd == "digest":
        since = _parse_since(rest)
        if isinstance(since, tuple):
            print(since[1], file=sys.stderr)
            return 1
        return run_digest(
            cfg,
            since_hours=since,
            skip_fetch=_parse_skip_fetch(rest),
            skip_wechat_inbox=_parse_skip_wechat_inbox(rest),
            skip_wechat_export=_parse_skip_wechat_export(rest),
            skip_wechat_sync=_parse_skip_wechat_sync(rest),
            fix=_parse_fix(rest),
        )
    if cmd == "setup":
        force = "--force" in rest
        return run_setup(cfg, force=force)
    if cmd == "config":
        return run_config_status(cfg)
    if cmd == "auth":
        return run_auth(cfg)
    if cmd == "fetch":
        channel = _parse_channel(rest)
        return run_fetch(cfg, channel=channel, fix=_parse_fix(rest))
    if cmd == "preflight":
        action = "fetch"
        if rest and not rest[0].startswith("-"):
            action = rest[0]
        return run_preflight(cfg, action=action, fix=_parse_fix(rest))
    if cmd == "channels":
        return _dispatch_channels(cfg, rest)
    if cmd == "status":
        return run_status(cfg)
    if cmd == "version":
        print(__version__)
        return 0
    if cmd == "wechat":
        return _dispatch_wechat(cfg, rest)
    print(f"未知命令: {cmd}", file=sys.stderr)
    return 1


def _parse_scope(args: list[str], default: str | None = None) -> str | None:
    if "--scope" not in args:
        return default
    idx = args.index("--scope")
    if idx + 1 >= len(args):
        return default
    return args[idx + 1]


def _parse_person(args: list[str]) -> str | None:
    if "--person" not in args:
        return None
    idx = args.index("--person")
    if idx + 1 >= len(args):
        return None
    return args[idx + 1]


def _parse_output_dir(args: list[str]) -> str | None:
    if "--output" not in args:
        return None
    idx = args.index("--output")
    if idx + 1 >= len(args):
        return None
    return args[idx + 1]


def _dispatch_channels(cfg, args: list[str]) -> int:
    action = args[0] if args else "list"
    if action in ("-h", "--help"):
        print(
            "用法:\n"
            "  channels list\n"
            "  channels add @username [--note 备注] [--disabled]\n"
            "  channels remove @username\n"
            "  channels enable @username\n"
            "  channels disable @username"
        )
        return 0
    if action == "list":
        return run_channels_list(cfg)
    if action == "add":
        if len(args) < 2:
            print("错误: channels add 需要 @username", file=sys.stderr)
            return 1
        note = ""
        if "--note" in args:
            idx = args.index("--note")
            if idx + 1 < len(args):
                note = args[idx + 1]
        return run_channels_add(
            cfg,
            args[1],
            note=note,
            enabled="--disabled" not in args,
        )
    if action == "remove":
        if len(args) < 2:
            print("错误: channels remove 需要 @username", file=sys.stderr)
            return 1
        return run_channels_remove(cfg, args[1])
    if action == "enable":
        if len(args) < 2:
            print("错误: channels enable 需要 @username", file=sys.stderr)
            return 1
        return run_channels_enable(cfg, args[1], enabled=True)
    if action == "disable":
        if len(args) < 2:
            print("错误: channels disable 需要 @username", file=sys.stderr)
            return 1
        return run_channels_enable(cfg, args[1], enabled=False)
    print(f"未知 channels 子命令: {action}", file=sys.stderr)
    return 1


def _dispatch_wechat(cfg, args: list[str]) -> int:
    if not args or args[0] in ("-h", "--help"):
        print(
            "用法: chat_radar wechat parse <file> | inbox | import | locate | status | "
            "sync [--since 24] [--scope groups|private|all] | "
            "summary [--since 24] [--scope all] [--from-db] [--person NAME] | "
            "keys derive | keys validate | digest [--since 24]"
        )
        return 0
    sub = args[0]
    if sub == "locate":
        return run_wechat_locate(cfg)
    if sub == "status":
        return run_wechat_status(cfg)
    if sub == "sync":
        since = _parse_since(args[1:])
        if isinstance(since, tuple):
            print(since[1], file=sys.stderr)
            return 1
        return run_wechat_sync(cfg, since_hours=since, scope=_parse_scope(args[1:]))
    if sub == "summary":
        since = _parse_since(args[1:])
        if isinstance(since, tuple):
            print(since[1], file=sys.stderr)
            return 1
        return run_wechat_summary(
            cfg,
            since_hours=since,
            scope=_parse_scope(args[1:]),
            from_db="--from-db" in args[1:],
            person=_parse_person(args[1:]),
            output_dir=_parse_output_dir(args[1:]),
        )
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
    if sub == "import":
        return run_wechat_import_exports(cfg)
    if sub == "keys":
        if len(args) < 2:
            print("用法: chat_radar wechat keys derive | validate", file=sys.stderr)
            return 1
        if args[1] == "derive":
            return run_wechat_keys_derive(cfg)
        if args[1] == "validate":
            return run_wechat_keys_validate(cfg)
        print("用法: chat_radar wechat keys derive | validate", file=sys.stderr)
        return 1
    if sub == "digest":
        since = _parse_since(args[1:])
        if isinstance(since, tuple):
            print(since[1], file=sys.stderr)
            return 1
        return run_wechat_digest(cfg, since_hours=since)
    print(f"未知 wechat 子命令: {sub}", file=sys.stderr)
    return 1
