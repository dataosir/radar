"""运行时路径解析."""

from __future__ import annotations

import os
from pathlib import Path


def base_dir() -> Path:
    env = os.environ.get("CHAT_RADAR_HOME") or os.environ.get("TG_RADAR_HOME")
    if env:
        return Path(env).expanduser().resolve()
    return Path.cwd().resolve()


def data_dir() -> Path:
    p = base_dir() / "data"
    p.mkdir(parents=True, exist_ok=True)
    return p


def reports_dir() -> Path:
    p = base_dir() / "reports"
    p.mkdir(parents=True, exist_ok=True)
    return p


def logs_dir() -> Path:
    p = base_dir() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_path() -> Path:
    env = os.environ.get("CHAT_RADAR_CONFIG") or os.environ.get("TG_RADAR_CONFIG")
    if env:
        return Path(env).expanduser().resolve()
    legacy = base_dir() / "tg_radar_config.json"
    current = base_dir() / "chat_radar_config.json"
    if current.exists():
        return current
    if legacy.exists():
        return legacy
    return current
