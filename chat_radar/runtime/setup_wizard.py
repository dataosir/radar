"""交互式首次配置向导."""

from __future__ import annotations

import platform
from pathlib import Path
from typing import Any

from chat_radar.config import ConfigStore
from chat_radar.core.paths import config_path, data_dir
from chat_radar.runtime.tg_runner import _session_exists, check_telegram_login


def _prompt(text: str, *, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{text}{suffix}: ").strip()
    return value or default


def _prompt_yes_no(text: str, *, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    value = input(f"{text} ({hint}): ").strip().lower()
    if not value:
        return default
    return value in ("y", "yes", "是", "1")


def _is_api_configured(cfg: ConfigStore) -> bool:
    api_id = int(cfg.get("telegram.api_id", 0) or 0)
    api_hash = str(cfg.get("telegram.api_hash", "") or "").strip()
    return bool(api_id) and api_hash not in ("", "REPLACE_ME")


def _print_api_guide() -> None:
    print()
    print("── 步骤 1/4：Telegram API 凭证 ──")
    print("1. 浏览器打开 https://my.telegram.org")
    print("2. 用手机号登录 → 进入「API development tools」")
    print("3. 创建应用，记下 api_id 和 api_hash")
    print()


def _configure_api(cfg: ConfigStore) -> None:
    _print_api_guide()
    current_id = int(cfg.get("telegram.api_id", 0) or 0)
    current_hash = str(cfg.get("telegram.api_hash", "") or "")

    while True:
        raw_id = _prompt("api_id", default=str(current_id) if current_id else "")
        try:
            api_id = int(raw_id)
            if api_id <= 0:
                raise ValueError
        except ValueError:
            print("  请输入正整数 api_id")
            continue
        break

    while True:
        api_hash = _prompt("api_hash", default=current_hash if current_hash not in ("", "REPLACE_ME") else "")
        if len(api_hash) >= 16:
            break
        print("  api_hash 太短，请检查是否复制完整")

    cfg.set("telegram.api_id", api_id)
    cfg.set("telegram.api_hash", api_hash)
    print("  ✓ API 凭证已设置")


def _configure_channels(cfg: ConfigStore) -> None:
    print()
    print("── 步骤 2/4：招聘频道 ──")
    print("填写你已订阅的 Telegram 招聘频道 @用户名（可多次添加，留空结束）")
    print()

    channels: list[dict[str, Any]] = []
    existing = cfg.raw().get("channels", [])
    if isinstance(existing, list):
        for ch in existing:
            if isinstance(ch, dict) and ch.get("username"):
                channels.append(dict(ch))

    while True:
        username = _prompt("频道 @username（留空结束）")
        if not username:
            break
        if not username.startswith("@"):
            username = f"@{username}"
        note = _prompt(f"  备注（{username}）", default="招聘频道")
        enabled = _prompt_yes_no(f"  启用 {username}？", default=True)
        channels.append({"username": username, "enabled": enabled, "note": note})
        print(f"  ✓ 已添加 {username}")

    if channels:
        cfg.set_section("channels", channels)
        enabled_count = sum(1 for c in channels if c.get("enabled"))
        print(f"  共 {len(channels)} 个频道，{enabled_count} 个已启用")
    else:
        print("  未添加频道（可稍后重新运行 setup）")


def _configure_filter(cfg: ConfigStore) -> None:
    print()
    print("── 步骤 3/4：过滤关键词（可选）──")
    print("留空则保持当前默认规则（Java / 远程 / 后端等）")
    print()

    if not _prompt_yes_no("是否自定义关键词？", default=False):
        return

    current_inc = cfg.get("filter.include_keywords", []) or []
    inc_text = _prompt("包含关键词（逗号分隔）", default=", ".join(current_inc))
    if inc_text:
        cfg.set("filter.include_keywords", [k.strip() for k in inc_text.split(",") if k.strip()])

    current_exc = cfg.get("filter.exclude_keywords", []) or []
    exc_text = _prompt("排除关键词（逗号分隔）", default=", ".join(current_exc))
    if exc_text:
        cfg.set("filter.exclude_keywords", [k.strip() for k in exc_text.split(",") if k.strip()])

    print("  ✓ 过滤规则已更新")


def _ensure_wechat_dirs(cfg: ConfigStore) -> None:
    root = data_dir().parent
    for key, default in (
        ("wechat.inbox_dir", "data/wechat_inbox"),
        ("wechat.export_dir", "data/wechat_exports"),
    ):
        rel = str(cfg.get(key, default) or default)
        path = Path(rel)
        if not path.is_absolute():
            path = root / path
        path.mkdir(parents=True, exist_ok=True)


def _configure_wechat(cfg: ConfigStore) -> None:
    print()
    print("── 步骤 4/4：微信模块（可选）──")
    print("MVP 支持：inbox 粘贴、PC 导出 TXT、macOS 本地库（需密钥）")
    print()

    current = bool(cfg.get("wechat.enabled", False))
    if not _prompt_yes_no("是否启用微信模块？", default=current):
        cfg.set("wechat.enabled", False)
        print("  微信模块保持关闭")
        return

    cfg.set("wechat.enabled", True)
    _ensure_wechat_dirs(cfg)
    print("  ✓ 已创建 data/wechat_inbox 与 data/wechat_exports")

    if platform.system() == "Darwin":
        if _prompt_yes_no("是否自动探测 macOS 微信数据目录？", default=True):
            from chat_radar.runtime.wechat_runner import run_wechat_locate

            run_wechat_locate(cfg)
        print()
        print("  macOS 本地库需一次性提取密钥：")
        print("    ./ops/extract_wechat_keys.sh")
    else:
        print("  非 macOS：可使用 inbox 粘贴或 PC 导出 TXT")

    watch_raw = _prompt(
        "仅同步/摘要这些群名（逗号分隔，留空=全部群）",
        default=", ".join(cfg.get("wechat.watch_chats", []) or []),
    )
    if watch_raw.strip():
        chats = [c.strip() for c in watch_raw.split(",") if c.strip()]
        cfg.set("wechat.watch_chats", chats)
        print(f"  ✓ watch_chats: {len(chats)} 个群")
    else:
        cfg.set("wechat.watch_chats", [])
        print("  ✓ watch_chats: 全部群")

    print("  ✓ 微信模块已启用")


def run_setup(cfg: ConfigStore, *, force: bool = False) -> int:
    print()
    print("╔══════════════════════════════════════╗")
    print("║     CHAT-RADAR  引导式配置向导       ║")
    print("╚══════════════════════════════════════╝")

    if _is_api_configured(cfg) and not force:
        print()
        if not _prompt_yes_no("检测到已有配置，是否重新配置？", default=False):
            print("已取消。运行 ./start.sh auth 登录，或 ./start.sh digest 生成报告。")
            return 0

    if not _is_api_configured(cfg) or force:
        _configure_api(cfg)

    _configure_channels(cfg)
    _configure_filter(cfg)
    _configure_wechat(cfg)

    cfg.set("meta.initialized", True)
    path = cfg.save()
    print()
    print(f"配置已保存 → {path}")
    print()
    print("下一步:")
    print("  1. ./start.sh auth     # 首次 Telegram 登录")
    print("  2. ./start.sh digest   # 拉取 + 生成每日 digest（含微信）")
    if cfg.get("wechat.enabled", False) and platform.system() == "Darwin":
        print("  3. ./ops/extract_wechat_keys.sh  # macOS 微信密钥（一次性）")
    if _prompt_yes_no("是否现在登录 Telegram？", default=True):
        from chat_radar.runtime.tg_runner import run_auth

        run_auth(cfg)
    return 0


def run_config_status(cfg: ConfigStore) -> int:
    """显示当前配置摘要."""
    path = config_path()
    print(f"配置文件: {path}")
    api_ok = _is_api_configured(cfg)
    print(f"Telegram API: {'已配置' if api_ok else '未配置'}")
    if api_ok:
        if not _session_exists(cfg):
            print("Telegram 登录: 未登录（运行 ./start.sh auth）")
        else:
            logged_in, detail = check_telegram_login(cfg)
            print(f"Telegram 登录: {detail}" if logged_in else f"未登录 — {detail}")
    channels = cfg.raw().get("channels", [])
    if isinstance(channels, list):
        enabled = [c for c in channels if isinstance(c, dict) and c.get("enabled")]
        print(f"频道: {len(channels)} 个配置，{len(enabled)} 个启用")
        for ch in channels:
            if not isinstance(ch, dict):
                continue
            ref = ch.get("username") or ch.get("id", "?")
            flag = "✓" if ch.get("enabled") else "·"
            print(f"  {flag} {ref}  {ch.get('note', '')}")
    inc = cfg.get("filter.include_keywords", []) or []
    print(f"包含关键词: {', '.join(inc[:8])}{'...' if len(inc) > 8 else ''}")
    wechat_on = "开启" if cfg.get("wechat.enabled", False) else "关闭"
    print(f"微信模块: {wechat_on}")
    if cfg.get("wechat.enabled", False):
        watch = cfg.get("wechat.watch_chats", []) or []
        if watch:
            print(f"  watch_chats: {', '.join(watch[:5])}{'...' if len(watch) > 5 else ''}")
        mac_dir = cfg.get("wechat.mac_data_dir", "") or "（未配置）"
        print(f"  mac_data_dir: {mac_dir}")
    return 0
