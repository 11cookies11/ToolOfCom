"""应用入口：初始化核心组件并启动 GUI。"""

from __future__ import annotations

import sys

try:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
except ImportError:  # pragma: no cover
    from PyQt6.QtCore import QTimer  # type: ignore
    from PyQt6.QtWidgets import QApplication  # type: ignore

from core.communication_manager import CommunicationManager
from core.event_bus import EventBus
from core.plugin_manager import PluginManager
from core.protocol_loader import ProtocolLoader
from ui.main_window import MainWindow


def main() -> None:
    bus = EventBus()
    comm = CommunicationManager(bus)
    protocol = ProtocolLoader(bus)
    plugins = PluginManager(bus, protocol=protocol)
    plugins.load_all()

    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow(bus, comm)
    window.show()

    print("ToolOfCOM started")

    QTimer.singleShot(0, lambda: bus.publish("ui.ready"))

    app.exec()


if __name__ == "__main__":
    main()
