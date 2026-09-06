"""Telegram 频道配置 CRUD."""

from __future__ import annotations

from typing import Any

from chat_radar.config import ConfigStore


def normalize_channel_ref(ref: str) -> str:
    """规范化频道标识：保留 @username 或数字 id 字符串."""
    ref = ref.strip()
    if not ref:
        raise ValueError("频道标识不能为空")
    if ref.startswith("@"):
        return ref
    if ref.lstrip("-").isdigit():
        return ref
    return f"@{ref.lstrip('@')}"


def get_channels(cfg: ConfigStore) -> list[dict[str, Any]]:
    channels = cfg.raw().get("channels", [])
    if not isinstance(channels, list):
        return []
    return [dict(c) for c in channels if isinstance(c, dict)]


def find_channel_index(channels: list[dict[str, Any]], ref: str) -> int | None:
    target = normalize_channel_ref(ref)
    target_lower = target.lower()
    for idx, ch in enumerate(channels):
        username = str(ch.get("username", "") or "")
        cid = str(ch.get("id", "") or "")
        candidates = {username, username.lower(), cid, f"@{username.lstrip('@')}".lower()}
        if target in candidates or target_lower in candidates:
            return idx
        if username and normalize_channel_ref(username).lower() == target_lower:
            return idx
    return None


def channels_add(
    cfg: ConfigStore,
    ref: str,
    *,
    note: str = "",
    enabled: bool = True,
) -> dict[str, Any]:
    ref = normalize_channel_ref(ref)
    channels = get_channels(cfg)
    idx = find_channel_index(channels, ref)
    entry: dict[str, Any] = {
        "username": ref,
        "enabled": enabled,
        "note": note,
    }
    if idx is not None:
        existing = channels[idx]
        entry["note"] = note or str(existing.get("note", ""))
        entry["enabled"] = enabled if note else bool(existing.get("enabled", enabled))
        channels[idx] = entry
        action = "updated"
    else:
        channels.append(entry)
        action = "added"
    cfg.set_section("channels", channels)
    cfg.save()
    return {"action": action, "channel": entry}


def channels_remove(cfg: ConfigStore, ref: str) -> dict[str, Any]:
    ref = normalize_channel_ref(ref)
    channels = get_channels(cfg)
    idx = find_channel_index(channels, ref)
    if idx is None:
        raise ValueError(f"未找到频道: {ref}")
    removed = channels.pop(idx)
    cfg.set_section("channels", channels)
    cfg.save()
    return {"action": "removed", "channel": removed}


def channels_set_enabled(cfg: ConfigStore, ref: str, *, enabled: bool) -> dict[str, Any]:
    ref = normalize_channel_ref(ref)
    channels = get_channels(cfg)
    idx = find_channel_index(channels, ref)
    if idx is None:
        raise ValueError(f"未找到频道: {ref}")
    channels[idx]["enabled"] = enabled
    cfg.set_section("channels", channels)
    cfg.save()
    return {"action": "enabled" if enabled else "disabled", "channel": channels[idx]}
