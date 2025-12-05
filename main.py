"""应用入口：初始化核心组件与界面。"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
except ImportError:  # pragma: no cover
    from PyQt6.QtCore import QTimer  # type: ignore
    from PyQt6.QtWidgets import QApplication  # type: ignore

from core.event_bus import EventBus
from core.plugin_manager import PluginManager
from core.protocol_loader import ProtocolLoader
from core.serial_manager import SerialManager
from ui.main_window import MainWindow


def main() -> None:
    bus = EventBus()
    serial = SerialManager(bus)
    protocol = ProtocolLoader(bus)
    plugins = PluginManager(bus, Path("plugins"))
    plugins.load_all()

    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow(bus, serial)
    window.show()

    print("ToolOfCOM started")

    # UI 渲染完成后再通知插件可扩展 UI
    QTimer.singleShot(0, lambda: bus.publish("ui.ready"))

    app.exec()


if __name__ == "__main__":
    main()
