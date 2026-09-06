"""核心交互节点结构化日志（JSONL，便于后续迭代与排障）."""

from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from chat_radar.core.paths import logs_dir

logger = logging.getLogger("chat_radar")


def interaction_log_path() -> Path:
    return logs_dir() / "interactions.jsonl"


def log_interaction(
    event: str,
    *,
    status: str = "ok",
    level: str = "info",
    **fields: Any,
) -> None:
    """追加一条结构化交互记录到 logs/interactions.jsonl."""
    record: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "status": status,
        "level": level,
    }
    for key, value in fields.items():
        if value is not None:
            record[key] = value

    path = interaction_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:
        logger.warning("写入 interaction log 失败: %s", exc)

    msg = f"[interaction] {event}"
    if fields:
        summary = ", ".join(f"{k}={v}" for k, v in fields.items() if k not in ("error",))
        if summary:
            msg = f"{msg} ({summary})"
    if status == "error":
        logger.error(msg)
    elif status == "skip":
        logger.info("%s [skip]", msg)
    else:
        logger.info(msg)


@contextmanager
def log_step(step: str, **fields: Any) -> Iterator[None]:
    """记录步骤 start/done/fail 及耗时（毫秒）."""
    started = time.monotonic()
    log_interaction(f"{step}.start", **fields)
    try:
        yield
    except Exception as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        log_interaction(
            f"{step}.fail",
            status="error",
            level="error",
            duration_ms=duration_ms,
            error=str(exc),
            **fields,
        )
        raise
    else:
        duration_ms = int((time.monotonic() - started) * 1000)
        log_interaction(f"{step}.done", duration_ms=duration_ms, **fields)


@contextmanager
def log_command(command: str, argv: list[str] | None = None) -> Iterator[None]:
    """记录 CLI 命令生命周期."""
    args_preview = " ".join(argv or [])
    fields = {"command": command}
    if args_preview:
        fields["args"] = args_preview
    started = time.monotonic()
    log_interaction("command.start", **fields)
    exit_code = 0
    try:
        yield
    except Exception as exc:
        exit_code = 1
        duration_ms = int((time.monotonic() - started) * 1000)
        log_interaction(
            "command.fail",
            status="error",
            level="error",
            duration_ms=duration_ms,
            exit_code=exit_code,
            error=str(exc),
            **fields,
        )
        raise
    else:
        duration_ms = int((time.monotonic() - started) * 1000)
        log_interaction(
            "command.done",
            duration_ms=duration_ms,
            exit_code=exit_code,
            **fields,
        )


def log_command_result(command: str, exit_code: int, *, argv: list[str] | None = None) -> None:
    """在已知 exit code 时补记 command 结束（用于非 context manager 路径）."""
    fields: dict[str, Any] = {"command": command, "exit_code": exit_code}
    if argv:
        fields["args"] = " ".join(argv)
    status = "ok" if exit_code == 0 else "error"
    level = "info" if exit_code == 0 else "error"
    log_interaction("command.exit", status=status, level=level, **fields)
