"""基于 Qt 的主窗口：负责通信选择与日志展示，不处理协议逻辑。"""

from __future__ import annotations

import binascii
from typing import List

try:
    from PySide6.QtCore import Signal
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
    from PyQt6.QtCore import pyqtSignal as Signal  # type: ignore
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
from core.communication_manager import CommunicationManager


class MainWindow(QMainWindow):
    log_signal = Signal(str)

    def __init__(self, bus: EventBus, comm: CommunicationManager) -> None:
        super().__init__()
        self.bus = bus
        self.comm = comm

        self.setWindowTitle("ToolOfCOM")
        self._build_ui()
        self._wire_events()
        self._refresh_ports()
        self._toggle_mode()  # 初始化控件可用性

    def _build_ui(self) -> None:
        # 通信方式
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Serial", "TCP"])

        # 串口控件
        self.port_combo = QComboBox()
        self.baud_edit = QLineEdit("115200")
        self.connect_serial_btn = QPushButton("连接串口")

        # TCP 控件
        self.ip_edit = QLineEdit("127.0.0.1")
        self.tcp_port_edit = QLineEdit("6000")
        self.connect_tcp_btn = QPushButton("连接 TCP")

        self.refresh_btn = QPushButton("刷新")
        self.close_btn = QPushButton("关闭连接")

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("连接方式"))
        top_bar.addWidget(self.mode_combo)
        top_bar.addWidget(self.refresh_btn)
        top_bar.addWidget(self.close_btn)

        serial_bar = QHBoxLayout()
        serial_bar.addWidget(QLabel("串口:"))
        serial_bar.addWidget(self.port_combo, 1)
        serial_bar.addWidget(QLabel("波特率:"))
        serial_bar.addWidget(self.baud_edit)
        serial_bar.addWidget(self.connect_serial_btn)

        tcp_bar = QHBoxLayout()
        tcp_bar.addWidget(QLabel("IP:"))
        tcp_bar.addWidget(self.ip_edit)
        tcp_bar.addWidget(QLabel("端口:"))
        tcp_bar.addWidget(self.tcp_port_edit)
        tcp_bar.addWidget(self.connect_tcp_btn)

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
        layout.addLayout(serial_bar)
        layout.addLayout(tcp_bar)
        layout.addWidget(self.log_view, 1)
        layout.addLayout(send_bar)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.log_signal.connect(self._append_log)

    def _wire_events(self) -> None:
        self.refresh_btn.clicked.connect(self._refresh_ports)
        self.mode_combo.currentIndexChanged.connect(self._toggle_mode)
        self.close_btn.clicked.connect(self._close_comm)
        self.connect_serial_btn.clicked.connect(self._connect_serial)
        self.connect_tcp_btn.clicked.connect(self._connect_tcp)
        self.send_btn.clicked.connect(self._send_data)

        self.bus.subscribe("comm.connected", self._on_comm_connected)
        self.bus.subscribe("comm.disconnected", lambda _: self._log("通信已断开"))
        self.bus.subscribe("comm.rx", self._on_comm_rx)
        self.bus.subscribe("comm.tx", self._on_comm_tx)
        self.bus.subscribe("comm.error", self._on_comm_error)

    def _refresh_ports(self) -> None:
        ports: List[str] = self.comm.list_serial_ports()
        self.port_combo.clear()
        self.port_combo.addItems(ports)
        self._log(f"检测到串口: {ports}" if ports else "未检测到串口")

    def _toggle_mode(self) -> None:
        is_serial = self.mode_combo.currentText() == "Serial"
        self.port_combo.setEnabled(is_serial)
        self.baud_edit.setEnabled(is_serial)
        self.connect_serial_btn.setEnabled(is_serial)

        self.ip_edit.setEnabled(not is_serial)
        self.tcp_port_edit.setEnabled(not is_serial)
        self.connect_tcp_btn.setEnabled(not is_serial)

    def _close_comm(self) -> None:
        self.comm.close()

    def _send_data(self) -> None:
        text = self.input_edit.text().strip()
        if not text:
            return
        data = self._parse_input(text)
        if data is None:
            self._log("输入格式错误，需 HEX 或 文本")
            return
        self.comm.send(data)

    def _parse_input(self, text: str) -> bytes | None:
        cleaned = text.replace(" ", "")
        if len(cleaned) % 2 == 0 and all(c in "0123456789abcdefABCDEF" for c in cleaned):
            try:
                return bytes.fromhex(cleaned)
            except Exception:
                return None
        try:
            return text.encode("utf-8")
        except Exception:
            return None

    def _on_comm_rx(self, data: bytes) -> None:
        hex_str = binascii.hexlify(data, sep=b" ").decode().upper()
        self._log(f"[RX] {hex_str}")

    def _on_comm_tx(self, data: bytes) -> None:
        hex_str = binascii.hexlify(data, sep=b" ").decode().upper()
        self._log(f"[TX] {hex_str}")

    def _on_comm_connected(self, info) -> None:
        self._log(f"连接成功: {info}")

    def _on_comm_error(self, reason) -> None:
        self._log(f"[ERROR] {reason}")

    def _connect_serial(self) -> None:
        port = self.port_combo.currentText()
        baud_text = self.baud_edit.text().strip() or "115200"
        if not port:
            self._log("未选择串口")
            return
        try:
            baud = int(baud_text)
        except ValueError:
            self._log("波特率格式错误")
            return
        self.comm.select_serial(port, baud)

    def _connect_tcp(self) -> None:
        ip = self.ip_edit.text().strip() or "127.0.0.1"
        port_text = self.tcp_port_edit.text().strip() or "6000"
        try:
            port = int(port_text)
        except ValueError:
            self._log("端口格式错误")
            return
        self.comm.select_tcp(ip, port)

    def _log(self, message: str) -> None:
        self.log_signal.emit(message)

    def _append_log(self, message: str) -> None:
        self.log_view.append(message)
        self.log_view.moveCursor(QTextCursor.End)


def run_app(bus: EventBus, comm: CommunicationManager) -> None:
    """便捷启动函数。"""
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow(bus, comm)
    win.show()
    app.exec()
