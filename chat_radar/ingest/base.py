"""输入适配器协议."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from chat_radar.core.models import RawMessage


class Ingestor(Protocol):
    """将外部 IM 数据转为 RawMessage 列表."""

    def ingest(self) -> list[RawMessage]: ...

    def ingest_file(self, path: Path) -> list[RawMessage]: ...
