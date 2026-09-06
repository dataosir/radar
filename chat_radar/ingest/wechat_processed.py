"""微信 inbox / export 已处理文件游标（避免重复解析）."""

from __future__ import annotations

import json
from pathlib import Path


def _load_state(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items()}


def _save_state(path: Path, state: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def file_signature(path: Path) -> str:
    stat = path.stat()
    return f"{stat.st_mtime_ns}:{stat.st_size}"


def is_processed(state_path: Path, path: Path) -> bool:
    state = _load_state(state_path)
    key = str(path.resolve())
    return state.get(key) == file_signature(path)


def mark_processed(state_path: Path, path: Path) -> None:
    state = _load_state(state_path)
    state[str(path.resolve())] = file_signature(path)
    _save_state(state_path, state)


def list_pending_files(
    directory: Path,
    *,
    state_path: Path,
    extensions: tuple[str, ...],
) -> list[Path]:
    if not directory.is_dir():
        return []
    pending: list[Path] = []
    for path in sorted(directory.iterdir()):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        if path.suffix.lower() not in extensions:
            continue
        if is_processed(state_path, path):
            continue
        pending.append(path)
    return pending
