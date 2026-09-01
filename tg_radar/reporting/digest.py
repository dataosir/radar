"""Markdown digest 渲染."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class DigestMeta:
    scanned_channels: int
    total_fetched: int
    total_matched: int
    generated_at: datetime


def render_digest_markdown(meta: DigestMeta, jobs: list[dict[str, Any]], *, summary_max: int = 300) -> str:
    ts = meta.generated_at.strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# TG-RADAR Digest · {ts}",
        "",
        "## 概览",
        f"- 扫描频道：{meta.scanned_channels}",
        f"- 新消息：{meta.total_fetched}",
        f"- 命中招聘：{meta.total_matched}",
        "",
    ]
    if not jobs:
        lines.append("_本次无命中。可检查 `filter.include_keywords` 或频道是否启用。_")
        lines.append("")
        return "\n".join(lines)

    lines.append("## 命中列表（新 → 旧）")
    lines.append("")
    for i, job in enumerate(jobs, 1):
        title = job.get("title") or "（无标题）"
        channel = job.get("channel_username") or job.get("channel_id", "?")
        date = job.get("date", "")
        rules = ", ".join(job.get("matched_rules") or [])
        link = job.get("link", "")
        summary = (job.get("summary") or "")[:summary_max]
        lines.extend(
            [
                f"### {i}. {title}",
                f"- **频道**：{channel}",
                f"- **时间**：{date}",
                f"- **规则**：{rules}",
                f"- **链接**：{link}",
                f"- **摘要**：{summary}",
                "",
                "---",
                "",
            ]
        )
    return "\n".join(lines)
