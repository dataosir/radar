"""扫描 export 目录中未处理的微信 PC 导出 TXT."""

from __future__ import annotations

from pathlib import Path

from chat_radar.core.models import RawMessage
from chat_radar.ingest.wechat_export import parse_export_file
from chat_radar.ingest.wechat_processed import list_pending_files, mark_processed


def scan_export_dir(
    export_dir: Path,
    *,
    state_path: Path,
    default_chat: str,
    timezone_name: str = "Asia/Shanghai",
    extensions: tuple[str, ...] = (".txt",),
) -> tuple[list[RawMessage], int]:
    """解析 export 目录中尚未处理的 TXT，返回消息与成功处理的文件数."""
    pending = list_pending_files(export_dir, state_path=state_path, extensions=extensions)
    messages: list[RawMessage] = []
    processed_count = 0
    for path in pending:
        chat_title = default_chat if default_chat != "export" else path.stem
        parsed = parse_export_file(path, chat_title=chat_title, timezone_name=timezone_name)
        if not parsed:
            continue
        messages.extend(parsed)
        mark_processed(state_path, path)
        processed_count += 1
    return messages, processed_count
