"""应用入口：初始化核心组件与界面。"""

from __future__ import annotations

from pathlib import Path

from core.event_bus import EventBus
from core.plugin_manager import PluginManager
from core.protocol_loader import ProtocolLoader
from core.serial_manager import SerialConfig, SerialManager
from ui.main_window import MainWindow


def bootstrap() -> None:
    bus = EventBus()
    plugins = PluginManager(Path("plugins"))
    plugins.discover()

    protocol = ProtocolLoader(Path("config/protocol.yaml"))
    protocol.load()

    serial = SerialManager(SerialConfig(port="COM1"))
    # TODO: 在此处根据配置打开串口、绑定事件

    ui = MainWindow()
    ui.show()


if __name__ == "__main__":
    bootstrap()
