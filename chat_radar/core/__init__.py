"""Layer 0 · 路径、原子写、日志."""

from .paths import base_dir, config_path, data_dir, logs_dir, reports_dir
from .utils import atomic_write_json, atomic_write_text, setup_logging

__all__ = [
    "atomic_write_json",
    "atomic_write_text",
    "base_dir",
    "config_path",
    "data_dir",
    "logs_dir",
    "reports_dir",
    "setup_logging",
]
