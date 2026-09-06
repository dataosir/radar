"""Telegram ingest / digest 编排."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from chat_radar.config import ConfigStore
from chat_radar.core.interaction_log import log_interaction, log_step
from chat_radar.core.paths import base_dir, data_dir, reports_dir
from chat_radar.core.models import RawMessage
from chat_radar.filter import RuleEngine
from chat_radar.ingest.cursors import cursors_path, commit_fetch_cursor, load_cursors
from chat_radar.ingest.persist import append_messages, load_recent_messages
from chat_radar.ingest.telethon_client import (
    TelegramIngestor,
    TelegramNotLoggedInError,
    session_file,
    session_storage_path,
)
from chat_radar.reporting.digest import DigestMeta, render_digest_markdown

logger = logging.getLogger("chat_radar")


def _telegram_configured(cfg: ConfigStore) -> tuple[int, str] | None:
    api_id = int(cfg.get("telegram.api_id", 0) or 0)
    api_hash = str(cfg.get("telegram.api_hash", "") or "").strip()
    if not api_id or not api_hash or api_hash == "REPLACE_ME":
        return None
    return api_id, api_hash


def _session_name(cfg: ConfigStore) -> str:
    return str(cfg.get("telegram.session_name", "chat_radar"))


def _session_exists(cfg: ConfigStore) -> bool:
    return session_storage_path(base_dir(), _session_name(cfg)).exists()


async def _verify_telegram_login(cfg: ConfigStore) -> tuple[bool, str]:
    """联网校验 session 是否已授权."""
    if _telegram_configured(cfg) is None:
        return False, "未配置 API"
    if not _session_exists(cfg):
        return False, "未找到登录会话文件"
    ingestor = _ingestor_from_config(cfg)
    try:
        await ingestor.connect()
        me = await ingestor.client.get_me()
        name = me.first_name or me.username or str(me.id)
        return True, f"已登录: {name}"
    except TelegramNotLoggedInError:
        return False, "会话未授权或已失效"
    finally:
        await ingestor.disconnect()


def check_telegram_login(cfg: ConfigStore) -> tuple[bool, str]:
    try:
        return asyncio.run(_verify_telegram_login(cfg))
    except Exception as exc:
        logger.warning("校验 Telegram 登录状态失败: %s", exc)
        return False, f"无法校验登录状态: {exc}"


def _ingestor_from_config(cfg: ConfigStore) -> TelegramIngestor:
    creds = _telegram_configured(cfg)
    if creds is None:
        raise ValueError("请先在 chat_radar_config.json 配置 telegram.api_id / api_hash")
    api_id, api_hash = creds
    return TelegramIngestor(
        api_id=api_id,
        api_hash=api_hash,
        session_path=session_file(base_dir(), _session_name(cfg)),
        data_dir=data_dir(),
        bootstrap_limit=int(cfg.get("ingest.bootstrap_limit", 50)),
        request_delay_seconds=float(cfg.get("ingest.request_delay_seconds", 1.0)),
    )


def _enabled_channels(cfg: ConfigStore) -> list[dict[str, Any]]:
    channels = cfg.raw().get("channels", [])
    if not isinstance(channels, list):
        return []
    return [c for c in channels if isinstance(c, dict) and c.get("enabled")]


def _channel_ref(channel: dict[str, Any]) -> str:
    username = channel.get("username")
    if username:
        return str(username)
    if channel.get("id"):
        return str(channel["id"])
    raise ValueError("频道配置缺少 username 或 id")


def _raw_messages_path() -> Path:
    return data_dir() / "raw_messages.jsonl"


def _jobs_path() -> Path:
    return data_dir() / "jobs.jsonl"


def _rule_engine(cfg: ConfigStore) -> RuleEngine:
    return RuleEngine(
        include_keywords=cfg.get("filter.include_keywords", []) or [],
        exclude_keywords=cfg.get("filter.exclude_keywords", []) or [],
        include_patterns=cfg.get("filter.include_patterns", []) or [],
    )


def _title_from_text(text: str) -> str:
    first = text.strip().splitlines()[0] if text.strip() else "（无标题）"
    return first[:80]


async def _fetch_all(cfg: ConfigStore, *, channel_filter: str | None = None) -> tuple[int, int]:
    channels = _enabled_channels(cfg)
    if channel_filter:
        needle = channel_filter.lstrip("@")
        channels = [
            c
            for c in channels
            if str(c.get("username", "")).lstrip("@") == needle or str(c.get("id", "")) == channel_filter
        ]
    if not channels:
        raise ValueError("没有启用的频道，请在 chat_radar_config.json 设置 channels[].enabled=true")

    ingestor = _ingestor_from_config(cfg)
    total_written = 0
    total_skipped = 0
    cursor_file = cursors_path(data_dir())
    try:
        await ingestor.connect()
        delay = float(cfg.get("ingest.request_delay_seconds", 1.0))
        for idx, channel in enumerate(channels):
            ref = _channel_ref(channel)
            messages = await ingestor.fetch_channel(ref)
            written, skipped = append_messages(_raw_messages_path(), messages)
            total_written += written
            total_skipped += skipped
            if messages:
                commit_fetch_cursor(cursor_file, messages)
            print(f"fetch {ref}: 拉取 {len(messages)} 条，写入 {written}，跳过重复 {skipped}")
            if idx + 1 < len(channels) and delay > 0:
                await asyncio.sleep(delay)
    finally:
        await ingestor.disconnect()
    return total_written, total_skipped


def run_auth(cfg: ConfigStore) -> int:
    if _telegram_configured(cfg) is None:
        print("尚未配置 Telegram API，请先运行引导配置：", file=sys.stderr)
        print("  ./start.sh setup   或   python -m chat_radar setup", file=sys.stderr)
        return 1

    async def _auth() -> None:
        ingestor = _ingestor_from_config(cfg)
        try:
            await ingestor.interactive_login()
        finally:
            await ingestor.disconnect()

    try:
        asyncio.run(_auth())
    except Exception as exc:
        logger.exception("auth 失败")
        print(f"auth 失败: {exc}", file=sys.stderr)
        return 2
    return 0


def _print_not_logged_in_help() -> None:
    print()
    print("尚未登录 Telegram，无法拉取频道消息。")
    print("请按顺序完成：")
    print("  1) ./start.sh setup   # 若尚未配置 API / 频道")
    print("  2) ./start.sh auth    # 用手机号 + 验证码登录")
    print("  3) ./start.sh fetch   # 再次拉取")


def run_preflight(
    cfg: ConfigStore,
    *,
    action: str = "fetch",
    fix: bool = False,
) -> int:
    """检查 fetch/digest 前置条件。返回码: 0=就绪, 1=未配置, 2=未登录, 3=无启用频道."""
    if _telegram_configured(cfg) is None:
        print("尚未配置 Telegram API。")
        print("请运行 ./start.sh setup（或菜单选「1) 首次配置」）")
        return 1

    if action in ("fetch", "digest") and not _enabled_channels(cfg):
        print("没有启用的 Telegram 频道。")
        print("请运行 ./start.sh setup，在引导中添加频道并选择「启用」")
        return 3

    logged_in, detail = check_telegram_login(cfg)
    if not logged_in:
        print(f"Telegram 登录: {detail}")
        _print_not_logged_in_help()
        if fix and sys.stdin.isatty():
            answer = input("是否现在登录？[Y/n]: ").strip().lower()
            if answer in ("", "y", "yes", "是"):
                code = run_auth(cfg)
                if code != 0:
                    return 2
                logged_in, detail = check_telegram_login(cfg)
                if not logged_in:
                    print(f"登录后仍无法校验: {detail}", file=sys.stderr)
                    return 2
                print(detail)
                return 0
        return 2

    print(detail)
    return 0


def run_fetch(cfg: ConfigStore, *, channel: str | None = None, fix: bool = False) -> int:
    code = run_preflight(cfg, action="fetch", fix=fix)
    if code != 0:
        return code

    try:
        written, skipped = asyncio.run(_fetch_all(cfg, channel_filter=channel))
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    except TelegramNotLoggedInError:
        _print_not_logged_in_help()
        return 2
    except Exception as exc:
        logger.exception("fetch 失败")
        print(f"fetch 失败: {exc}", file=sys.stderr)
        return 2

    print(f"fetch 完成：写入 {written}，跳过重复 {skipped}")
    return 0


def _digest_sources(cfg: ConfigStore) -> set[str]:
    sources = {"telegram"}
    if cfg.get("wechat.enabled", False):
        sources.add("wechat")
    return sources


def _source_label(source: str) -> str:
    return {"telegram": "Telegram", "wechat": "微信"}.get(source, source)


def _count_by_source(messages: list[RawMessage]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for msg in messages:
        label = _source_label(msg.source)
        counts[label] = counts.get(label, 0) + 1
    return counts


def _load_recent_messages(cfg: ConfigStore, since_hours: int | None) -> list[RawMessage]:
    return load_recent_messages(
        _raw_messages_path(),
        since_hours=since_hours,
        sources=_digest_sources(cfg),
    )


def _append_jobs(jobs: list[dict[str, Any]]) -> int:
    if not jobs:
        return 0
    path = _jobs_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: set[str] = set()
    if path.exists():
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                existing.add(str(data.get("id", "")))

    written = 0
    with path.open("a", encoding="utf-8") as fh:
        for job in jobs:
            job_id = str(job.get("id", ""))
            if job_id in existing:
                continue
            fh.write(json.dumps(job, ensure_ascii=False) + "\n")
            existing.add(job_id)
            written += 1
    return written


def run_digest(
    cfg: ConfigStore,
    *,
    since_hours: int | None = 24,
    skip_fetch: bool = False,
    skip_wechat_inbox: bool = False,
    skip_wechat_export: bool = False,
    skip_wechat_sync: bool = False,
    fix: bool = False,
) -> int:
    from chat_radar.runtime.wechat_runner import run_wechat_ingest_for_digest

    log_interaction(
        "digest.start",
        since_hours=since_hours,
        skip_fetch=skip_fetch,
        skip_wechat_inbox=skip_wechat_inbox,
        skip_wechat_export=skip_wechat_export,
        skip_wechat_sync=skip_wechat_sync,
    )

    wechat_enabled = bool(cfg.get("wechat.enabled", False))
    if wechat_enabled:
        with log_step("digest.wechat_ingest", since_hours=since_hours):
            run_wechat_ingest_for_digest(
                cfg,
                since_hours=since_hours,
                skip_inbox=skip_wechat_inbox,
                skip_export=skip_wechat_export,
                skip_sync=skip_wechat_sync,
            )

    if not skip_fetch and _enabled_channels(cfg):
        if _telegram_configured(cfg) is None:
            log_interaction("digest.fetch", status="skip", reason="telegram_not_configured")
            print("提示：未配置 Telegram API，跳过 fetch（仅对本地数据生成 digest）", file=sys.stderr)
        else:
            code = run_preflight(cfg, action="digest", fix=fix)
            if code == 2:
                raw_path = _raw_messages_path()
                if raw_path.exists() and raw_path.stat().st_size > 0:
                    log_interaction("digest.fetch", status="skip", reason="telegram_not_logged_in")
                    print("提示：未登录，跳过 fetch，仅用本地已有数据生成 digest", file=sys.stderr)
                else:
                    return code
            elif code not in (0,):
                return code
            else:
                try:
                    with log_step("digest.telegram_fetch"):
                        written, skipped = asyncio.run(_fetch_all(cfg))
                    print(f"fetch 完成：写入 {written}，跳过重复 {skipped}")
                    log_interaction(
                        "digest.telegram_fetch",
                        written=written,
                        skipped=skipped,
                    )
                except TelegramNotLoggedInError:
                    _print_not_logged_in_help()
                    return 2
                except Exception as exc:
                    logger.exception("digest 内 fetch 失败")
                    print(f"fetch 失败: {exc}", file=sys.stderr)
                    return 2
    elif skip_fetch:
        log_interaction("digest.fetch", status="skip", reason="skip_fetch_flag")

    with log_step("digest.load_messages", since_hours=since_hours):
        messages = _load_recent_messages(cfg, since_hours)
    engine = _rule_engine(cfg)
    summary_max = int(cfg.get("report.summary_max_chars", 300))

    jobs: list[dict[str, Any]] = []
    digest_jobs: list[dict[str, Any]] = []
    for msg in messages:
        result = engine.evaluate(msg.text)
        if not result.matched:
            continue
        job_id = f"{msg.source}:{msg.source_id}:{msg.message_id}"
        job = {
            "id": job_id,
            "channel_id": msg.source_id,
            "message_id": msg.message_id,
            "title": _title_from_text(msg.text),
            "channel_username": msg.chat_title or msg.source_id,
            "sender": msg.sender,
            "date": msg.date,
            "matched_rules": result.rules,
            "link": msg.link,
            "summary": msg.text[:summary_max],
            "source": msg.source,
            "status": "new",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        jobs.append(job)
        digest_jobs.append(job)

    jobs_written = _append_jobs(jobs)
    digest_jobs.sort(key=lambda j: j.get("date", ""), reverse=True)
    source_matched: dict[str, int] = {}
    for job in digest_jobs:
        label = _source_label(str(job.get("source", "telegram")))
        source_matched[label] = source_matched.get(label, 0) + 1
    meta = DigestMeta(
        scanned_channels=len({m.chat_title or m.source_id for m in messages}),
        total_fetched=len(messages),
        total_matched=len(digest_jobs),
        generated_at=datetime.now(timezone.utc),
        source_fetched=_count_by_source(messages),
        source_matched=source_matched or None,
    )
    md = render_digest_markdown(meta, digest_jobs, summary_max=summary_max, title_prefix="CHAT-RADAR")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = reports_dir() / f"DIGEST_{ts}.md"
    out_path.write_text(md, encoding="utf-8")
    fetched_by_source = ", ".join(f"{k} {v}" for k, v in sorted(meta.source_fetched.items())) if meta.source_fetched else ""
    print(
        f"digest: 消息 {len(messages)}"
        + (f"（{fetched_by_source}）" if fetched_by_source else "")
        + f"，命中 {len(digest_jobs)}，新 jobs {jobs_written} → {out_path}"
    )
    log_interaction(
        "digest.done",
        messages=len(messages),
        matched=len(digest_jobs),
        jobs_written=jobs_written,
        output=str(out_path),
        source_fetched=meta.source_fetched,
        source_matched=meta.source_matched,
    )
    return 0


def run_channels_list(cfg: ConfigStore) -> int:
    from chat_radar.config.channels import get_channels

    channels = get_channels(cfg)
    if not channels:
        print("未配置 channels")
        print("添加示例: python -m chat_radar channels add @your_jobs_channel --note 招聘")
        return 0

    cursors = load_cursors(cursors_path(data_dir()))
    print(f"{'频道':<30} {'启用':<6} 备注")
    print("-" * 60)
    for ch in channels:
        ref = str(ch.get("username") or ch.get("id", "?"))
        enabled = "是" if ch.get("enabled") else "否"
        note = str(ch.get("note", ""))[:30]
        print(f"{ref:<30} {enabled:<6} {note}")

    enabled_count = sum(1 for ch in channels if ch.get("enabled"))
    print(f"\n共 {len(channels)} 个频道，{enabled_count} 个已启用")

    if cursors:
        print("\n游标（channel_id → last_message_id）:")
        for cid, entry in sorted(cursors.items()):
            last = entry.get("last_message_id", "—")
            updated = entry.get("updated_at", "")
            print(f"  {cid}: {last}  ({updated})")
    else:
        print("\n尚无游标（首次 fetch 后生成）")
    return 0


def run_channels_add(
    cfg: ConfigStore,
    ref: str,
    *,
    note: str = "",
    enabled: bool = True,
) -> int:
    from chat_radar.config.channels import channels_add

    try:
        result = channels_add(cfg, ref, note=note, enabled=enabled)
    except ValueError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    ch = result["channel"]
    action = "已更新" if result["action"] == "updated" else "已添加"
    state = "启用" if ch.get("enabled") else "禁用"
    print(f"{action}频道 {ch.get('username')}（{state}）")
    if ch.get("note"):
        print(f"  备注: {ch['note']}")
    return 0


def run_channels_remove(cfg: ConfigStore, ref: str) -> int:
    from chat_radar.config.channels import channels_remove

    try:
        result = channels_remove(cfg, ref)
    except ValueError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    ch = result["channel"]
    print(f"已删除频道 {ch.get('username') or ch.get('id')}")
    return 0


def run_channels_enable(cfg: ConfigStore, ref: str, *, enabled: bool) -> int:
    from chat_radar.config.channels import channels_set_enabled

    try:
        result = channels_set_enabled(cfg, ref, enabled=enabled)
    except ValueError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    ch = result["channel"]
    verb = "已启用" if enabled else "已禁用"
    print(f"{verb}频道 {ch.get('username') or ch.get('id')}")
    return 0
