"""基于 Qt 的主窗口，仅负责展示与操作串口，不处理协议逻辑。"""

from __future__ import annotations

import binascii
from typing import List

try:
    from PySide6.QtCore import Qt, Signal
    from PySide6.QtGui import QTextCursor
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError:  # pragma: no cover
    from PyQt6.QtCore import Qt, pyqtSignal as Signal  # type: ignore
    from PyQt6.QtGui import QTextCursor  # type: ignore
    from PyQt6.QtWidgets import (  # type: ignore
        QApplication,
        QComboBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

from core.event_bus import EventBus
from core.serial_manager import SerialManager


class MainWindow(QMainWindow):
    log_signal = Signal(str)

    def __init__(self, bus: EventBus, serial: SerialManager) -> None:
        super().__init__()
        self.bus = bus
        self.serial = serial

        self.setWindowTitle("ToolOfCOM")
        self._build_ui()
        self._wire_events()
        self._refresh_ports()

    def _build_ui(self) -> None:
        self.port_combo = QComboBox()
        self.refresh_btn = QPushButton("刷新")
        self.open_btn = QPushButton("打开串口")
        self.close_btn = QPushButton("关闭串口")

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("串口:"))
        top_bar.addWidget(self.port_combo, 1)
        top_bar.addWidget(self.refresh_btn)
        top_bar.addWidget(self.open_btn)
        top_bar.addWidget(self.close_btn)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)

        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("输入 HEX（如: 55 AA 01）或文本")
        self.send_btn = QPushButton("发送")

        send_bar = QHBoxLayout()
        send_bar.addWidget(self.input_edit, 1)
        send_bar.addWidget(self.send_btn)

        layout = QVBoxLayout()
        layout.addLayout(top_bar)
        layout.addWidget(self.log_view, 1)
        layout.addLayout(send_bar)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.log_signal.connect(self._append_log)

    def _wire_events(self) -> None:
        self.refresh_btn.clicked.connect(self._refresh_ports)
        self.open_btn.clicked.connect(self._open_serial)
        self.close_btn.clicked.connect(self._close_serial)
        self.send_btn.clicked.connect(self._send_data)

        self.bus.subscribe("serial.opened", lambda _: self._log("串口已打开"))
        self.bus.subscribe("serial.closed", lambda _: self._log("串口已关闭"))
        self.bus.subscribe("serial.rx", self._on_serial_rx)
        self.bus.subscribe("serial.tx", self._on_serial_tx)

    def _refresh_ports(self) -> None:
        ports: List[str] = self.serial.list_ports()
        self.port_combo.clear()
        self.port_combo.addItems(ports)
        self._log(f"检测到串口: {ports}" if ports else "未检测到串口")

    def _open_serial(self) -> None:
        port = self.port_combo.currentText()
        if not port:
            self._log("未选择串口")
            return
        self.serial.open(port=port, baudrate=115200)

    def _close_serial(self) -> None:
        self.serial.close()

    def _send_data(self) -> None:
        text = self.input_edit.text().strip()
        if not text:
            return
        data = self._parse_input(text)
        if data is None:
            self._log("输入格式错误，需 HEX 或 文本")
            return
        self.serial.send(data)

    def _parse_input(self, text: str) -> bytes | None:
        # 优先尝试 HEX
        cleaned = text.replace(" ", "")
        if len(cleaned) % 2 == 0 and all(c in "0123456789abcdefABCDEF" for c in cleaned):
            try:
                return bytes.fromhex(cleaned)
            except Exception:
                return None
        # 回退 UTF-8 文本
        try:
            return text.encode("utf-8")
        except Exception:
            return None

    def _on_serial_rx(self, data: bytes) -> None:
        hex_str = binascii.hexlify(data, sep=b" ").decode().upper()
        self._log(f"[RX] {hex_str}")

    def _on_serial_tx(self, data: bytes) -> None:
        hex_str = binascii.hexlify(data, sep=b" ").decode().upper()
        self._log(f"[TX] {hex_str}")

    def _log(self, message: str) -> None:
        self.log_signal.emit(message)

    def _append_log(self, message: str) -> None:
        self.log_view.append(message)
        self.log_view.moveCursor(QTextCursor.End)


def run_app(bus: EventBus, serial: SerialManager) -> None:
    """便捷启动函数。"""
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow(bus, serial)
    win.show()
    app.exec()
