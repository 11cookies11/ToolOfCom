"""插件管理：动态加载插件模块，每个插件自行在 register(bus) 中订阅事件。"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import sys
from pathlib import Path
from types import ModuleType
from typing import Dict, List, Optional

from core.event_bus import EventBus
from utils.path_utils import resolve_resource_path


class PluginManager:
    def __init__(self, bus: EventBus, plugin_dir: str | Path | None = None, protocol=None) -> None:
        self.bus = bus
        self.protocol = protocol
        self.plugin_dir = resolve_resource_path(plugin_dir or "plugins")
        self._plugins: Dict[str, ModuleType] = {}

    def load_all(self) -> None:
        """遍历目录加载全部插件。"""
        if not self.plugin_dir.exists():
            self._log(f"[WARN] 插件目录不存在: {self.plugin_dir}")
            return
        for path in self.plugin_dir.glob("*.py"):
            if path.name.startswith("_"):
                continue
            self.load(path.stem)

    def load(self, name: str) -> None:
        """加载指定插件文件。"""
        path = self.plugin_dir / f"{name}.py"
        if not path.exists():
            self._publish_error(f"插件不存在: {path}")
            return

        try:
            module = self._import_module(name, path)
            if not hasattr(module, "register"):
                raise AttributeError(f"插件缺少 register: {name}")
            self._call_register(module)
            self._plugins[name] = module
            self._log(f"插件已加载: {name}")
            self.bus.publish("plugin.loaded", name)
        except Exception as exc:
            self._publish_error(f"加载插件失败 {name}: {exc}")

    def list_plugins(self) -> List[str]:
        return list(self._plugins.keys())

    def reload(self, name: str) -> None:
        """热更新插件。"""
        module = self._plugins.get(name)
        if not module:
            self.load(name)
            return
        try:
            reloaded = importlib.reload(module)
            if not hasattr(reloaded, "register"):
                raise AttributeError(f"插件缺少 register: {name}")
            self._call_register(reloaded)
            self._plugins[name] = reloaded
            self._log(f"插件已重载: {name}")
            self.bus.publish("plugin.loaded", name)
        except Exception as exc:
            self._publish_error(f"重载插件失败 {name}: {exc}")

    def _call_register(self, module: ModuleType) -> None:
        """根据 register 签名决定是否传入 protocol。"""
        register = module.register
        sig = inspect.signature(register)
        params = sig.parameters
        if len(params) >= 2 or any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params.values()):
            register(self.bus, self.protocol)
        else:
            register(self.bus)

    def _import_module(self, name: str, path: Path) -> ModuleType:
        """从文件路径加载模块，不要求 plugins 目录是包。"""
        spec = importlib.util.spec_from_file_location(f"plugins.{name}", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"无法为插件创建 spec: {name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    def _publish_error(self, message: str) -> None:
        self._log(f"[ERROR] {message}")
        self.bus.publish("plugin.error", message)

    @staticmethod
    def _log(msg: str) -> None:
        print(f"[PluginManager] {msg}")
