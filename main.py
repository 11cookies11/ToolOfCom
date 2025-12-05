"""应用入口：初始化核心组件与界面。"""

from __future__ import annotations

from pathlib import Path

from core.event_bus import EventBus
from core.plugin_manager import PluginManager
from core.protocol_loader import ProtocolLoader
from core.serial_manager import SerialManager
from ui.main_window import MainWindow


def bootstrap() -> None:
    bus = EventBus()
    plugins = PluginManager(Path("plugins"))
    plugins.discover()

    protocol = ProtocolLoader(bus)

    serial = SerialManager(bus)

    ui = MainWindow()
    ui.show()


if __name__ == "__main__":
    bootstrap()
