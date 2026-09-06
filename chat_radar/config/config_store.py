"""配置读写与默认值."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from chat_radar.core.paths import config_path

DEFAULTS: dict[str, Any] = {
    "meta.initialized": False,
    "meta.profile_summary": "",
    "telegram.api_id": 0,
    "telegram.api_hash": "",
    "telegram.session_name": "chat_radar",
    "ingest.bootstrap_limit": 50,
    "ingest.request_delay_seconds": 1.0,
    "filter.include_keywords": [],
    "filter.exclude_keywords": [],
    "filter.include_patterns": [],
    "report.summary_max_chars": 300,
    "report.timezone": "Asia/Shanghai",
    "log.level": "INFO",
    "log.redact_bodies": False,
    "wechat.enabled": False,
    "wechat.inbox_dir": "data/wechat_inbox",
    "wechat.default_chat": "inbox",
    "wechat.export_dir": "data/wechat_exports",
    "wechat.mac_data_dir": "",
    "wechat.keys_file": "data/wechat_keys.json",
    "wechat.decrypted_cache_dir": "data/wechat_decrypted",
    "wechat.watch_chats": [],
    "wechat.sync_scope": "groups",
    "wechat.summary_scope": "all",
    "wechat.summary_output_dir": "reports/wechat_contacts",
    "wechat.summary_body_max_chars": 500,
    "wechat.summary_text_only": True,
    "wechat.self_display_name": "我",
}


class ConfigStore:
    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data = data if data is not None else {}

    def get(self, dotted: str, default: Any = None) -> Any:
        if dotted in DEFAULTS and default is None:
            default = DEFAULTS[dotted]
        parts = dotted.split(".")
        cur: Any = self._data
        for p in parts:
            if not isinstance(cur, dict) or p not in cur:
                return default
            cur = cur[p]
        return cur

    def set(self, dotted: str, value: Any) -> None:
        parts = dotted.split(".")
        cur = self._data
        for p in parts[:-1]:
            nxt = cur.get(p)
            if not isinstance(nxt, dict):
                nxt = {}
                cur[p] = nxt
            cur = nxt
        cur[parts[-1]] = value

    def set_section(self, key: str, value: Any) -> None:
        """设置顶层配置段（如 channels 列表）."""
        self._data[key] = value

    def raw(self) -> dict[str, Any]:
        return deepcopy(self._data)

    def save(self, path: Path | None = None) -> Path:
        target = path or config_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(self._data, ensure_ascii=False, indent=2) + "\n"
        tmp = target.with_suffix(".json.tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(target)
        return target


def load_config(path: Path | None = None) -> ConfigStore:
    target = path or config_path()
    if not target.exists():
        return ConfigStore({})
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"配置文件必须是 JSON 对象: {target}")
    return ConfigStore(data)
