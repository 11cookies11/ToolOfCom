"""协议装载器占位：解析 YAML 协议定义，生成帧编解码器。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


class ProtocolLoader:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.spec: Dict[str, Any] = {}

    def load(self) -> Dict[str, Any]:
        with self.path.open("r", encoding="utf-8") as f:
            self.spec = yaml.safe_load(f) or {}
        return self.spec

    def get_command(self, name: str) -> Dict[str, Any]:
        return self.spec.get("commands", {}).get(name, {})
