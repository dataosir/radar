"""微信 ingest 编排."""

from __future__ import annotations

import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from chat_radar.config import ConfigStore
from chat_radar.core.interaction_log import log_interaction, log_step
from chat_radar.core.models import RawMessage
from chat_radar.core.paths import data_dir, reports_dir
from chat_radar.filter import RuleEngine
from chat_radar.ingest.persist import append_messages, load_recent_messages
from chat_radar.ingest.wechat_db_crypto import (
    DecryptStats,
    WeChatCryptoError,
    decrypt_tree,
    load_keys_file,
)
from chat_radar.ingest.wechat_db_reader import ReadStats, read_messages_from_decrypted
from chat_radar.ingest.wechat_export import parse_export_file
from chat_radar.ingest.wechat_export_watch import scan_export_dir
from chat_radar.ingest.wechat_inbox import scan_inbox_dir
from chat_radar.ingest.wechat_mac_paths import (
    WeChatMacAccount,
    discover_mac_wechat,
    pick_active_account,
    pick_primary_account,
    summarize_account,
)
from chat_radar.ingest.wechat_keys import (
    derive_and_save_keys,
    inspect_keys_file,
    load_saved_passphrase,
)
from chat_radar.ingest.wechat_processed import list_pending_files
from chat_radar.reporting.digest import DigestMeta, render_digest_markdown
from chat_radar.reporting.wechat_person_summary import (
    filter_plain_text_messages,
    group_messages_by_person,
    write_person_summaries,
)


def _raw_messages_path() -> Path:
    return data_dir() / "raw_messages.jsonl"


def _jobs_path() -> Path:
    return data_dir() / "jobs.jsonl"


def _inbox_state_path(cfg: ConfigStore) -> Path:
    return _resolve_data_path(cfg, "wechat.inbox_state_file", "data/wechat_inbox_processed.json")


def _export_state_path(cfg: ConfigStore) -> Path:
    return _resolve_data_path(cfg, "wechat.export_state_file", "data/wechat_export_processed.json")


def _export_dir(cfg: ConfigStore) -> Path:
    return _resolve_data_path(cfg, "wechat.export_dir", "data/wechat_exports")


def _inbox_dir(cfg: ConfigStore) -> Path:
    return _resolve_data_path(cfg, "wechat.inbox_dir", "data/wechat_inbox")


def _wechat_enabled(cfg: ConfigStore) -> bool:
    return bool(cfg.get("wechat.enabled", False))


def _rule_engine(cfg: ConfigStore) -> RuleEngine:
    return RuleEngine(
        include_keywords=cfg.get("filter.include_keywords", []) or [],
        exclude_keywords=cfg.get("filter.exclude_keywords", []) or [],
        include_patterns=cfg.get("filter.include_patterns", []) or [],
    )


def run_wechat_parse(cfg: ConfigStore, file_path: str, *, chat_title: str | None = None) -> int:
    if not _wechat_enabled(cfg):
        print("错误：wechat.enabled 未开启，请在 chat_radar_config.json 设置 wechat.enabled=true", file=sys.stderr)
        return 1

    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        print(f"错误：文件不存在: {path}", file=sys.stderr)
        return 1

    title = chat_title or cfg.get("wechat.default_chat", path.stem)
    tz = cfg.get("report.timezone", "Asia/Shanghai")
    messages = parse_export_file(path, chat_title=title, timezone_name=tz)
    if not messages:
        print(f"未解析到消息: {path}", file=sys.stderr)
        return 1

    written, skipped = append_messages(_raw_messages_path(), messages)
    print(f"wechat parse: {path.name} → 解析 {len(messages)} 条，写入 {written}，跳过重复 {skipped}")
    return 0


def run_wechat_inbox(cfg: ConfigStore) -> int:
    if not _wechat_enabled(cfg):
        print("错误：wechat.enabled 未开启", file=sys.stderr)
        return 1

    inbox = _inbox_dir(cfg)
    tz = cfg.get("report.timezone", "Asia/Shanghai")
    default_chat = cfg.get("wechat.default_chat", "inbox")
    state_path = _inbox_state_path(cfg)
    pending = list_pending_files(inbox, state_path=state_path, extensions=(".txt", ".md"))
    if not pending:
        print(f"inbox 无新文件: {inbox}")
        return 0

    messages = scan_inbox_dir(
        inbox,
        default_chat=default_chat,
        timezone_name=tz,
        state_path=state_path,
    )
    if not messages:
        print(f"inbox 文件无法解析: {inbox}")
        return 0

    written, skipped = append_messages(_raw_messages_path(), messages)
    print(
        f"wechat inbox: 新文件 {len(pending)} 个，解析 {len(messages)} 条，"
        f"写入 {written}，跳过重复 {skipped}"
    )
    return 0


def run_wechat_import_exports(cfg: ConfigStore, *, soft: bool = False) -> int:
    """扫描 export 目录中未处理的 TXT 并入库."""
    if not _wechat_enabled(cfg):
        if soft:
            return 0
        print("错误：wechat.enabled 未开启", file=sys.stderr)
        return 1

    export_dir = _export_dir(cfg)
    export_dir.mkdir(parents=True, exist_ok=True)
    tz = cfg.get("report.timezone", "Asia/Shanghai")
    default_chat = str(cfg.get("wechat.default_chat", "export") or "export")
    state_path = _export_state_path(cfg)
    pending = list_pending_files(export_dir, state_path=state_path, extensions=(".txt",))
    if not pending:
        print(f"wechat import: export 目录无新文件 ({export_dir})")
        return 0

    messages, processed_files = scan_export_dir(
        export_dir,
        state_path=state_path,
        default_chat=default_chat,
        timezone_name=tz,
    )
    if not messages:
        print(f"wechat import: {len(pending)} 个文件未解析到消息")
        return 0

    written, skipped = append_messages(_raw_messages_path(), messages)
    print(
        f"wechat import: 新文件 {processed_files} 个，解析 {len(messages)} 条，"
        f"写入 {written}，跳过重复 {skipped}"
    )
    return 0


def _load_recent_wechat_messages(since_hours: int | None) -> list[RawMessage]:
    return load_recent_messages(
        _raw_messages_path(),
        since_hours=since_hours,
        sources={"wechat"},
    )


def _title_from_text(text: str) -> str:
    first = text.strip().splitlines()[0] if text.strip() else "（无标题）"
    return first[:80]


def _normalize_since_hours(since_hours: int | None) -> int | None:
    """0 表示全量历史."""
    if since_hours == 0:
        return None
    return since_hours


def _normalize_scope(scope: str | None, default: str = "groups") -> str:
    value = (scope or default).strip().lower()
    if value not in ("groups", "private", "all"):
        raise ValueError(f"无效 scope: {scope}（可选 groups/private/all）")
    return value


def _resolve_account(cfg: ConfigStore) -> WeChatMacAccount | None:
    mac_dir = str(cfg.get("wechat.mac_data_dir", "") or "")
    account = _account_from_mac_dir(mac_dir) if mac_dir else None
    if account is None:
        account = pick_primary_account(discover_mac_wechat())
    return account


def _print_read_warnings(stats: ReadStats, decrypt_stats: DecryptStats | None = None) -> None:
    """输出诊断信息（不完整数据时帮助排查）."""
    for warning in stats.warnings():
        print(f"  提示: {warning}")
    if decrypt_stats:
        if decrypt_stats.skipped_no_key:
            print(f"  提示: {len(decrypt_stats.skipped_no_key)} 个库无密钥（覆盖率不足）")
        if decrypt_stats.failed:
            print(f"  提示: {len(decrypt_stats.failed)} 个库解密失败")


def _decrypt_account_dbs(
    cfg: ConfigStore,
    account: WeChatMacAccount,
) -> tuple[Path, list[Path], DecryptStats]:
    keys_path = _resolve_data_path(cfg, "wechat.keys_file", "data/wechat_keys.json")
    cache_dir = _resolve_data_path(cfg, "wechat.decrypted_cache_dir", "data/wechat_decrypted")

    inspection = inspect_keys_file(keys_path, account)
    if not inspection.ok:
        issues = "; ".join(inspection.issues) or "密钥文件无效"
        raise WeChatCryptoError(f"密钥检查未通过: {issues}")

    keys = load_keys_file(keys_path)
    decrypt_stats = DecryptStats()
    decrypted = decrypt_tree(account.db_storage, cache_dir, keys, stats=decrypt_stats)
    if not decrypted:
        raise WeChatCryptoError("未解密任何数据库（检查密钥文件是否覆盖 message/contact 库）")
    return cache_dir, decrypted, decrypt_stats


def _load_wechat_messages_from_db(
    cfg: ConfigStore,
    *,
    since_hours: int | None,
    scope: str,
    account: WeChatMacAccount | None = None,
    text_only: bool = False,
) -> tuple[list[RawMessage], ReadStats, DecryptStats]:
    acct = account or _resolve_account(cfg)
    if acct is None:
        raise FileNotFoundError("未找到微信数据目录，请先运行: python -m chat_radar wechat locate")

    cache_dir, _, decrypt_stats = _decrypt_account_dbs(cfg, acct)
    watch = cfg.get("wechat.watch_chats", []) or []
    tz = cfg.get("report.timezone", "Asia/Shanghai")
    self_name = str(cfg.get("wechat.self_display_name", "我") or "我")
    read_stats = ReadStats()
    messages = read_messages_from_decrypted(
        cache_dir,
        since_hours=_normalize_since_hours(since_hours),
        timezone_name=tz,
        chat_names=watch if watch else None,
        scope=scope,
        self_wxid=acct.wxid,
        self_display_name=self_name,
        text_only=text_only,
        stats=read_stats,
    )
    return messages, read_stats, decrypt_stats


def _resolve_data_path(cfg: ConfigStore, key: str, default: str) -> Path:
    raw = cfg.get(key, default)
    path = Path(str(raw)).expanduser()
    if not path.is_absolute():
        path = data_dir().parent / path
    return path


def run_wechat_locate(cfg: ConfigStore) -> int:
    """扫描本机微信数据目录（无需 wechat.enabled）."""
    if platform.system() != "Darwin":
        print("wechat locate 当前仅支持 macOS", file=sys.stderr)
        return 1

    override = cfg.get("wechat.mac_data_dir", "") or ""
    discovery = discover_mac_wechat()
    print("CHAT-RADAR · 微信本地数据探测")
    if discovery.wechat_version:
        print(f"微信版本: {discovery.wechat_version}")
    if override:
        print(f"配置覆盖目录: {override}")
    if not discovery.searched_roots:
        print("未找到微信数据目录（请确认已安装并登录过微信 PC 版）")
        return 1

    print("已扫描:")
    for root in discovery.searched_roots:
        print(f"  - {root}")

    if not discovery.accounts:
        print("未发现 wxid 账号目录")
        return 1

    for idx, acct in enumerate(discovery.accounts, start=1):
        summary = summarize_account(acct)
        print(f"\n账号 {idx}: {summary['wxid']}")
        print(f"  db_storage: {summary['db_storage']}")
        print(f"  message_*.db: {summary['message_db_count']} 个")
        print(f"  最近活跃: {summary['last_active']}")
        enc = "是（需密钥解密）" if summary["sample_encrypted"] else "否/未知"
        print(f"  加密库: {enc}")

    active = pick_active_account(discovery)
    primary = pick_primary_account(discovery)
    if active and len(discovery.accounts) > 1:
        print(f"\n当前活跃账号（最近登录）: {active.wxid}")
    if primary:
        keys_hint = _resolve_data_path(cfg, "wechat.keys_file", "data/wechat_keys.json")
        print("\n下一步:")
        print("  1. 运行 ./ops/extract_wechat_keys.sh 提取密钥 →", keys_hint)
        print("     或已有 passphrase 时: python -m chat_radar wechat keys derive")
        print("  2. chat_radar_config.json 设置 wechat.enabled=true")
        print("  3. python -m chat_radar wechat sync --since 24")
        print("  4. python -m chat_radar wechat summary --from-db --since 0  # 按联系人生成 MD")
        cfg.set("wechat.mac_data_dir", str(primary.db_storage.parent))
        cfg.save()
        print(f"\n已自动写入 wechat.mac_data_dir → {primary.db_storage.parent}")
    return 0


def _account_from_mac_dir(mac_dir: str) -> WeChatMacAccount | None:
    root = Path(mac_dir).expanduser()
    if not root.is_dir():
        return None
    if root.name.startswith("wxid_") and (root / "db_storage").is_dir():
        return WeChatMacAccount(wxid=root.name, root=root, db_storage=root / "db_storage")
    if root.name == "db_storage" and root.parent.name.startswith("wxid_"):
        parent = root.parent
        return WeChatMacAccount(wxid=parent.name, root=parent, db_storage=root)
    return None


def run_wechat_sync(
    cfg: ConfigStore,
    *,
    since_hours: int | None = 24,
    scope: str | None = None,
    soft: bool = False,
) -> int:
    """解密本地微信库并增量导入 raw_messages.jsonl."""
    if not _wechat_enabled(cfg):
        if soft:
            log_interaction("wechat.sync", status="skip", reason="wechat_disabled")
            return 0
        print("错误：wechat.enabled 未开启", file=sys.stderr)
        return 1
    if platform.system() != "Darwin":
        if soft:
            print("提示：非 macOS，跳过 wechat sync", file=sys.stderr)
            return 0
        print("wechat sync 当前仅支持 macOS", file=sys.stderr)
        return 1

    keys_path = _resolve_data_path(cfg, "wechat.keys_file", "data/wechat_keys.json")
    if not keys_path.exists():
        if soft:
            log_interaction("wechat.sync", status="skip", reason="keys_missing", keys_path=str(keys_path))
            print(f"提示：未找到密钥文件，跳过 wechat sync（{keys_path}）", file=sys.stderr)
            return 0
        print(f"错误：未找到密钥文件: {keys_path}", file=sys.stderr)
        print("提示：运行 ./ops/extract_wechat_keys.sh 或菜单「提取微信密钥」", file=sys.stderr)
        return 1

    try:
        effective_scope = _normalize_scope(scope or cfg.get("wechat.sync_scope", "groups"))
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    account = _resolve_account(cfg)
    if account is None:
        print("未找到微信数据目录，请先运行: python -m chat_radar wechat locate", file=sys.stderr)
        return 1

    try:
        messages, read_stats, decrypt_stats = _load_wechat_messages_from_db(
            cfg,
            since_hours=since_hours,
            scope=effective_scope,
            account=account,
        )
    except WeChatCryptoError as exc:
        if soft:
            print(f"提示：跳过 wechat sync — {exc}", file=sys.stderr)
            return 0
        print(f"错误：{exc}", file=sys.stderr)
        print("提示：运行 python -m chat_radar wechat keys validate 检查密钥", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        if soft:
            print(f"提示：跳过 wechat sync — {exc}", file=sys.stderr)
            return 0
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    since_label = "全量" if _normalize_since_hours(since_hours) is None else f"近 {since_hours}h"
    if not messages:
        print(f"wechat sync: {since_label} 无消息（scope={effective_scope}）")
        _print_read_warnings(read_stats, decrypt_stats)
        log_interaction(
            "wechat.sync",
            status="ok",
            wxid=account.wxid,
            scope=effective_scope,
            parsed=0,
            written=0,
            skipped=0,
        )
        return 0

    written, skipped = append_messages(_raw_messages_path(), messages)
    print(
        f"wechat sync: 账号 {account.wxid}，scope={effective_scope}，"
        f"解析 {len(messages)} 条，写入 {written}，跳过重复 {skipped}"
    )
    _print_read_warnings(read_stats, decrypt_stats)
    log_interaction(
        "wechat.sync",
        wxid=account.wxid,
        scope=effective_scope,
        parsed=len(messages),
        written=written,
        skipped=skipped,
        skipped_non_text=read_stats.skipped_non_text,
        skipped_system=read_stats.skipped_system,
    )
    return 0


def run_wechat_summary(
    cfg: ConfigStore,
    *,
    since_hours: int | None = 24,
    scope: str | None = None,
    from_db: bool = False,
    person: str | None = None,
    output_dir: str | None = None,
) -> int:
    """按联系人维度生成 Markdown 聊天记录摘要."""
    if not _wechat_enabled(cfg):
        print("错误：wechat.enabled 未开启", file=sys.stderr)
        return 1

    try:
        effective_scope = _normalize_scope(
            scope or cfg.get("wechat.summary_scope", "all"),
            default="all",
        )
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    self_name = str(cfg.get("wechat.self_display_name", "我") or "我")
    body_max = int(cfg.get("wechat.summary_body_max_chars", 500))
    text_only = bool(cfg.get("wechat.summary_text_only", True))
    since = _normalize_since_hours(since_hours)

    if from_db:
        if platform.system() != "Darwin":
            print("wechat summary --from-db 当前仅支持 macOS", file=sys.stderr)
            return 1
        try:
            messages, read_stats, decrypt_stats = _load_wechat_messages_from_db(
                cfg,
                since_hours=since_hours,
                scope=effective_scope,
                text_only=text_only,
            )
        except WeChatCryptoError as exc:
            print(f"错误：{exc}", file=sys.stderr)
            return 1
        except FileNotFoundError as exc:
            print(f"错误：{exc}", file=sys.stderr)
            return 1
    else:
        messages = _load_recent_wechat_messages(since)
        if effective_scope != "all":
            if effective_scope == "groups":
                messages = [m for m in messages if "@chatroom" in (m.link or "")]
            else:
                messages = [m for m in messages if "@chatroom" not in (m.link or "")]
        if text_only:
            messages = filter_plain_text_messages(messages)

    if not messages:
        since_label = "全量" if since is None else f"近 {since_hours}h"
        print(f"wechat summary: {since_label} 无可用消息（scope={effective_scope}）")
        return 0

    grouped = group_messages_by_person(messages, self_name=self_name)
    out_raw = output_dir or cfg.get("wechat.summary_output_dir", "reports/wechat_contacts")
    out_path = Path(str(out_raw)).expanduser()
    if not out_path.is_absolute():
        out_path = reports_dir().parent / out_path if str(out_raw).startswith("reports/") else data_dir().parent / out_path

    generated_at = datetime.now(timezone.utc)
    try:
        written = write_person_summaries(
            grouped,
            out_path,
            generated_at=generated_at,
            body_max_chars=body_max,
            self_name=self_name,
            only_person=person,
        )
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    since_label = "全量" if since is None else f"近 {since_hours}h"
    mode_label = "纯文本" if text_only else "全部类型"
    print(
        f"wechat summary: {since_label}（{mode_label}），联系人 {len(grouped)}，"
        f"消息 {len(messages)}，输出 {len(written)} 个文件 → {out_path}"
    )
    if from_db:
        _print_read_warnings(read_stats, decrypt_stats)
    return 0


def run_wechat_status(cfg: ConfigStore) -> int:
    """微信模块健康检查（目录、密钥、工具链）."""
    print("CHAT-RADAR · 微信状态")
    enabled = bool(cfg.get("wechat.enabled", False))
    print(f"  enabled: {'是' if enabled else '否'}")

    if platform.system() != "Darwin":
        print("  平台: 非 macOS（本地库读取不可用；仍可用 export/inbox）")
        return 0

    discovery = discover_mac_wechat()
    if discovery.wechat_version:
        print(f"  微信版本: {discovery.wechat_version}")
    print(f"  账号数: {len(discovery.accounts)}")

    account = _resolve_account(cfg)
    if account is None:
        print("  数据目录: 未配置（运行 wechat locate）")
    else:
        summary = summarize_account(account)
        print(f"  当前账号: {account.wxid}")
        print(f"  最近活跃: {summary['last_active']}")
        print(f"  message 库: {summary['message_db_count']} 个")

    keys_path = _resolve_data_path(cfg, "wechat.keys_file", "data/wechat_keys.json")
    inspection = inspect_keys_file(keys_path, account)
    if inspection.exists:
        pct = int(inspection.coverage_ratio * 100)
        print(f"  密钥文件: {keys_path}（{inspection.key_count} keys，覆盖率约 {pct}%）")
        for issue in inspection.issues:
            print(f"    ⚠ {issue}")
    else:
        print(f"  密钥文件: 缺失（{keys_path}）")

    zstd_ok = shutil.which("zstd") is not None
    print(f"  zstd: {'已安装' if zstd_ok else '未安装（压缩消息将跳过）'}")

    passphrase_ok = load_saved_passphrase() is not None
    print(f"  passphrase 缓存: {'有' if passphrase_ok else '无'}")

    cache_dir = _resolve_data_path(cfg, "wechat.decrypted_cache_dir", "data/wechat_decrypted")
    if cache_dir.is_dir():
        cached_dbs = sum(1 for _ in cache_dir.rglob("*.db"))
        print(f"  解密缓存: {cached_dbs} 个库")
    else:
        print("  解密缓存: 无")

    inbox = _inbox_dir(cfg)
    if inbox.is_dir():
        pending = list_pending_files(inbox, state_path=_inbox_state_path(cfg), extensions=(".txt", ".md"))
        print(f"  inbox 待处理: {len(pending)} 个新文件")
    else:
        print(f"  inbox: 目录不存在 ({inbox})")

    export_dir = _export_dir(cfg)
    if export_dir.is_dir():
        pending_export = list_pending_files(
            export_dir, state_path=_export_state_path(cfg), extensions=(".txt",)
        )
        print(f"  export 待处理: {len(pending_export)} 个新 TXT")
    return 0


def format_wechat_status_lines(cfg: ConfigStore) -> list[str]:
    """供统一 status 使用的紧凑摘要行."""
    lines: list[str] = []
    enabled = _wechat_enabled(cfg)
    lines.append(f"微信: {'开启' if enabled else '关闭'}")
    if not enabled:
        return lines

    if platform.system() != "Darwin":
        inbox = _inbox_dir(cfg)
        pending = 0
        if inbox.is_dir():
            pending = len(
                list_pending_files(inbox, state_path=_inbox_state_path(cfg), extensions=(".txt", ".md"))
            )
        lines.append(f"  inbox 待处理: {pending} 个（本地库需 macOS）")
        return lines

    account = _resolve_account(cfg)
    if account:
        summary = summarize_account(account)
        lines.append(f"  账号: {account.wxid}（活跃 {summary['last_active']}）")
    else:
        lines.append("  账号: 未配置（运行 wechat locate）")

    keys_path = _resolve_data_path(cfg, "wechat.keys_file", "data/wechat_keys.json")
    inspection = inspect_keys_file(keys_path, account)
    if inspection.ok:
        pct = int(inspection.coverage_ratio * 100)
        lines.append(f"  密钥: ✅ {pct}% 覆盖")
    elif inspection.exists:
        lines.append("  密钥: ⚠ 覆盖率不足")
    else:
        lines.append("  密钥: 缺失（需 extract_wechat_keys.sh）")

    inbox = _inbox_dir(cfg)
    pending_inbox = 0
    if inbox.is_dir():
        pending_inbox = len(
            list_pending_files(inbox, state_path=_inbox_state_path(cfg), extensions=(".txt", ".md"))
        )
    lines.append(f"  inbox 待处理: {pending_inbox} 个")
    return lines


def run_wechat_ingest_for_digest(
    cfg: ConfigStore,
    *,
    since_hours: int | None = 24,
    skip_inbox: bool = False,
    skip_export: bool = False,
    skip_sync: bool = False,
) -> int:
    """digest 前串联微信 ingest：inbox → export → sync（均可 soft skip）."""
    if not _wechat_enabled(cfg):
        log_interaction("wechat.ingest", status="skip", reason="wechat_disabled")
        return 0
    if not skip_inbox:
        with log_step("wechat.inbox"):
            run_wechat_inbox(cfg)
    else:
        log_interaction("wechat.inbox", status="skip", reason="skip_inbox_flag")
    if not skip_export:
        with log_step("wechat.import"):
            run_wechat_import_exports(cfg, soft=True)
    else:
        log_interaction("wechat.import", status="skip", reason="skip_export_flag")
    if not skip_sync:
        with log_step("wechat.sync", since_hours=since_hours):
            run_wechat_sync(cfg, since_hours=since_hours, soft=True)
    else:
        log_interaction("wechat.sync", status="skip", reason="skip_sync_flag")
    return 0


def run_wechat_keys_validate(cfg: ConfigStore) -> int:
    """校验密钥文件与当前账号是否匹配."""
    account = _resolve_account(cfg)
    keys_path = _resolve_data_path(cfg, "wechat.keys_file", "data/wechat_keys.json")
    inspection = inspect_keys_file(keys_path, account)

    print(f"密钥文件: {keys_path}")
    if inspection.wxid:
        print(f"  绑定账号: {inspection.wxid}")
    if inspection.active_account:
        print(f"  当前活跃账号: {inspection.active_account}")
    if inspection.total_dbs:
        pct = int(inspection.coverage_ratio * 100)
        print(f"  覆盖率: {inspection.key_count} keys / {inspection.total_dbs} dbs（约 {pct}%）")

    if inspection.ok:
        print("结果: ✅ 密钥文件可用")
        return 0

    print("结果: ❌ 密钥文件有问题")
    for issue in inspection.issues:
        print(f"  - {issue}")
    if load_saved_passphrase():
        print("建议: sudo .venv/bin/python ops/derive_wechat_keys.py")
    else:
        print("建议: ./ops/extract_wechat_keys.sh")
    return 1


def run_wechat_digest(cfg: ConfigStore, *, since_hours: int | None = 24) -> int:
    if not _wechat_enabled(cfg):
        print("错误：wechat.enabled 未开启", file=sys.stderr)
        return 1

    messages = _load_recent_wechat_messages(since_hours)
    engine = _rule_engine(cfg)
    summary_max = int(cfg.get("report.summary_max_chars", 300))

    jobs: list[dict] = []
    for msg in messages:
        result = engine.evaluate(msg.text)
        if not result.matched:
            continue
        jobs.append(
            {
                "title": _title_from_text(msg.text),
                "channel_username": msg.chat_title or msg.source_id,
                "sender": msg.sender,
                "date": msg.date,
                "matched_rules": result.rules,
                "link": msg.link,
                "summary": msg.text[:summary_max],
                "source": "wechat",
            }
        )

    jobs.sort(key=lambda j: j.get("date", ""), reverse=True)
    meta = DigestMeta(
        scanned_channels=len({m.chat_title for m in messages}),
        total_fetched=len(messages),
        total_matched=len(jobs),
        generated_at=datetime.now(timezone.utc),
    )
    md = render_digest_markdown(meta, jobs, summary_max=summary_max, title_prefix="CHAT-RADAR")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = reports_dir() / f"DIGEST_wechat_{ts}.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"wechat digest: 消息 {len(messages)}，命中 {len(jobs)} → {out_path}")
    return 0


def run_wechat_keys_derive(cfg: ConfigStore) -> int:
    """从已保存的 passphrase 派生密钥（多账号自动匹配）."""
    if platform.system() != "Darwin":
        print("wechat keys derive 当前仅支持 macOS", file=sys.stderr)
        return 1

    keys_path = _resolve_data_path(cfg, "wechat.keys_file", "data/wechat_keys.json")
    passphrase = load_saved_passphrase()
    if not passphrase:
        print(
            "错误：未找到 passphrase。请先运行 ./ops/extract_wechat_keys.sh 完成 LLDB 捕获",
            file=sys.stderr,
        )
        return 1

    print("从已保存的 passphrase 派生密钥（自动匹配账号）...")
    try:
        account, ok_count, total_salts = derive_and_save_keys(keys_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    keys_path.chmod(0o600)
    cfg.set("wechat.mac_data_dir", str(account.db_storage.parent))
    cfg.save()
    print(f"完成: {keys_path}")
    print(f"  账号: {account.wxid}")
    print(f"  密钥: {ok_count}/{total_salts} salts 验证通过")
    print(f"  已写入 wechat.mac_data_dir → {account.db_storage.parent}")
    print("\n下一步:")
    print("  python -m chat_radar wechat summary --from-db --since 0 --scope all")
    return 0
