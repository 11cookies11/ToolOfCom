"""插件管理占位：动态发现与加载插件。"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import Any, Dict


class PluginManager:
    def __init__(self, plugin_dir: Path) -> None:
        self.plugin_dir = plugin_dir
        self.plugins: Dict[str, Any] = {}

    def discover(self) -> None:
        for module_info in pkgutil.iter_modules([str(self.plugin_dir)]):
            name = module_info.name
            try:
                module = importlib.import_module(f"plugins.{name}")
                self.plugins[name] = module
            except Exception:
                # 生产环境可接入日志
                pass

    def get(self, name: str) -> Any:
        return self.plugins.get(name)
