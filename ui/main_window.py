"""基于 Qt 的主窗口：整合手动串口/TCP助手与 DSL 脚本执行。"""

from __future__ import annotations

import binascii
import codecs
from pathlib import Path
from typing import List, Optional

import yaml

try:
    from PySide6.QtCore import Signal
    from PySide6.QtGui import QTextCursor
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QFileDialog,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPlainTextEdit,
        QProgressBar,
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
        QFileDialog,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPlainTextEdit,
        QProgressBar,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

from core.communication_manager import CommunicationManager
from core.event_bus import EventBus
from ui.script_runner_qt import ScriptRunnerQt


class MainWindow(QMainWindow):
    log_signal = Signal(object)

    def __init__(self, bus: EventBus, comm: CommunicationManager) -> None:
        super().__init__()
        self.bus = bus
        self.comm = comm
        self.script_runner: Optional[ScriptRunnerQt] = None
        self.mode: str = "manual"  # manual | script

        self.display_mode = "hex"
        self._text_decoder = codecs.getincrementaldecoder("utf-8")()
        self._rx_text_buffer: str = ""
        self.setWindowTitle("ToolOfCOM")
        self._build_ui()
        self._wire_events()
        self._refresh_ports()
        self._toggle_manual_comm_mode()

    # -------------------- UI 构建 --------------------
    def _build_ui(self) -> None:
        # 顶部模式+脚本控制
        self.mode_label = QLabel("Mode: Manual")
        self.run_script_btn = QPushButton("Run Script")
        self.stop_script_btn = QPushButton("Stop Script")
        self.stop_script_btn.setEnabled(False)
        self.load_yaml_btn = QPushButton("Load YAML")

        top_bar = QHBoxLayout()
        top_bar.addWidget(self.mode_label)
        top_bar.addStretch()
        top_bar.addWidget(self.load_yaml_btn)
        top_bar.addWidget(self.run_script_btn)
        top_bar.addWidget(self.stop_script_btn)

        # Script 区域
        self.yaml_edit = QPlainTextEdit()
        self.yaml_edit.setPlaceholderText("在此编辑 YAML，或点击 Load YAML 载入文件")
        self.script_state_label = QLabel("State: idle")
        self.script_progress = QProgressBar()
        self.script_progress.setRange(0, 100)
        self.script_log = QTextEdit()
        self.script_log.setReadOnly(True)

        script_box = QVBoxLayout()
        script_box.addWidget(QLabel("YAML 脚本"))
        script_box.addWidget(self.yaml_edit, 2)
        script_box.addWidget(self.script_state_label)
        script_box.addWidget(self.script_progress)
        script_box.addWidget(QLabel("脚本日志"))
        script_box.addWidget(self.script_log, 1)

        # 通信方式
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Serial", "TCP"])
        self.refresh_btn = QPushButton("刷新")
        self.close_btn = QPushButton("关闭连接")
        self.display_combo = QComboBox()
        self.display_combo.addItems(["HEX", "Text"])

        top_comm = QHBoxLayout()
        top_comm.addWidget(QLabel("连接方式"))
        top_comm.addWidget(self.mode_combo)
        top_comm.addWidget(self.refresh_btn)
        top_comm.addWidget(self.close_btn)
        top_comm.addWidget(QLabel("显示格式"))
        top_comm.addWidget(self.display_combo)

        # 串口控制
        self.port_combo = QComboBox()
        self.baud_edit = QLineEdit("115200")
        self.connect_serial_btn = QPushButton("连接串口")

        serial_bar = QHBoxLayout()
        serial_bar.addWidget(QLabel("串口:"))
        serial_bar.addWidget(self.port_combo, 1)
        serial_bar.addWidget(QLabel("波特率"))
        serial_bar.addWidget(self.baud_edit)
        serial_bar.addWidget(self.connect_serial_btn)

        # TCP 控制
        self.ip_edit = QLineEdit("127.0.0.1")
        self.tcp_port_edit = QLineEdit("6000")
        self.connect_tcp_btn = QPushButton("连接 TCP")

        tcp_bar = QHBoxLayout()
        tcp_bar.addWidget(QLabel("IP:"))
        tcp_bar.addWidget(self.ip_edit)
        tcp_bar.addWidget(QLabel("端口:"))
        tcp_bar.addWidget(self.tcp_port_edit)
        tcp_bar.addWidget(self.connect_tcp_btn)

        # 发送/接收
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)

        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("输入 HEX（如: 55 AA 01）")
        self.send_btn = QPushButton("发送")

        send_bar = QHBoxLayout()
        send_bar.addWidget(self.input_edit, 1)
        send_bar.addWidget(self.send_btn)

        manual_box = QVBoxLayout()
        manual_box.addLayout(top_comm)
        manual_box.addLayout(serial_bar)
        manual_box.addLayout(tcp_bar)
        manual_box.addWidget(self.log_view, 1)
        manual_box.addLayout(send_bar)

        # 左右布局
        mid = QHBoxLayout()
        mid.addLayout(script_box, 2)
        mid.addLayout(manual_box, 1)

        layout = QVBoxLayout()
        layout.addLayout(top_bar)
        layout.addLayout(mid)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.log_signal.connect(self._append_log)

    # -------------------- 事件绑定 --------------------
    def _wire_events(self) -> None:
        self.refresh_btn.clicked.connect(self._refresh_ports)
        self.mode_combo.currentIndexChanged.connect(self._toggle_manual_comm_mode)
        self.close_btn.clicked.connect(self._close_comm)
        self.connect_serial_btn.clicked.connect(self._connect_serial)
        self.connect_tcp_btn.clicked.connect(self._connect_tcp)
        self.send_btn.clicked.connect(self._send_data)
        self.display_combo.currentIndexChanged.connect(self._change_display_mode)

        self.load_yaml_btn.clicked.connect(self._load_yaml_file)
        self.run_script_btn.clicked.connect(self._run_script)
        self.stop_script_btn.clicked.connect(self._stop_script)

        self.bus.subscribe("comm.connected", self._on_comm_connected)
        self.bus.subscribe("comm.disconnected", lambda _: self._log("通信已断开"))
        self.bus.subscribe("comm.rx", self._on_comm_rx)
        self.bus.subscribe("comm.tx", self._on_comm_tx)
        self.bus.subscribe("comm.error", self._on_comm_error)

    # -------------------- 手动通信 --------------------
    def _refresh_ports(self) -> None:
        ports: List[str] = self.comm.list_serial_ports()
        self.port_combo.clear()
        self.port_combo.addItems(ports)
        self._log(f"检测到串口: {ports}" if ports else "未检测到串口")

    def _toggle_manual_comm_mode(self) -> None:
        is_serial = self.mode_combo.currentText() == "Serial"
        self.port_combo.setEnabled(is_serial and self.mode == "manual")
        self.baud_edit.setEnabled(is_serial and self.mode == "manual")
        self.connect_serial_btn.setEnabled(is_serial and self.mode == "manual")

        self.ip_edit.setEnabled((not is_serial) and self.mode == "manual")
        self.tcp_port_edit.setEnabled((not is_serial) and self.mode == "manual")
        self.connect_tcp_btn.setEnabled((not is_serial) and self.mode == "manual")

    def _change_display_mode(self) -> None:
        self.display_mode = self.display_combo.currentText().lower()
        self._text_decoder = codecs.getincrementaldecoder("utf-8")()
        self._rx_text_buffer = ""
        if self.display_mode == "hex":
            self.input_edit.setPlaceholderText("输入 HEX（如: 55 AA 01）")
        else:
            self.input_edit.setPlaceholderText("输入文本（UTF-8）")

    def _set_display_mode(self, mode: str) -> None:
        """Force switch display/input mode by value ('hex' or 'text')."""
        mode = (mode or "").lower()
        if mode not in {"hex", "text"}:
            return
        target_text = "HEX" if mode == "hex" else "Text"
        if self.display_combo.currentText().lower() == mode:
            # ensure placeholder/decoder are refreshed
            self._change_display_mode()
        else:
            idx = self.display_combo.findText(target_text)
            if idx >= 0:
                self.display_combo.setCurrentIndex(idx)

    def _close_comm(self) -> None:
        self.comm.close()

    def _send_data(self) -> None:
        text = self.input_edit.text().strip()
        if not text:
            return
        data = self._parse_input(text)
        if data is None:
            if self.display_mode == "hex":
                self._log("输入格式错误，需要 HEX（如 55 AA 01）")
            else:
                self._log("输入格式错误，需要可编码为 UTF-8 的文本")
            return
        self.comm.send(data)

    def _parse_input(self, text: str) -> bytes | None:
        if self.display_mode == "hex":
            cleaned = text.replace(" ", "")
            if len(cleaned) % 2 != 0 or not cleaned:
                return None
            try:
                return bytes.fromhex(cleaned)
            except Exception:
                return None
        # text mode
        try:
            return text.encode("utf-8")
        except Exception:
            return None

    def _format_payload(self, data: bytes, *, stream: bool = False) -> str:
        if self.display_mode == "text":
            if stream:
                return self._text_decoder.decode(data, final=False)
            return data.decode("utf-8", errors="replace")
        return binascii.hexlify(data, sep=b" ").decode().upper()

    def _on_comm_rx(self, data: bytes) -> None:
        if self.display_mode == "text":
            decoded = self._format_payload(data, stream=True)
            combined = self._rx_text_buffer + decoded
            lines = combined.splitlines(keepends=True)
            self._rx_text_buffer = ""
            for line in lines:
                if line.endswith("\n") or line.endswith("\r"):
                    clean = line.rstrip("\r\n")
                    if clean:
                        self._log(f"[RX] {clean}")
                else:
                    self._rx_text_buffer += line
            if len(self._rx_text_buffer) > 1024:
                self._log(f"[RX] {self._rx_text_buffer}")
                self._rx_text_buffer = ""
            return

        payload = self._format_payload(data, stream=False)
        self._log(f"[RX] {payload}")

    def _on_comm_tx(self, data: bytes) -> None:
        payload = self._format_payload(data, stream=False)
        self._log(f"[TX] {payload}")

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

    # -------------------- Script 集成 --------------------
    def _load_yaml_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择 YAML 脚本", str(Path.cwd()), "YAML Files (*.yaml *.yml)")
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8")
            self.yaml_edit.setPlainText(text)
            self._log_script(f"加载脚本: {path}")
            try:
                data = yaml.safe_load(text) or {}
                if isinstance(data, dict):
                    ui_cfg = data.get("ui", {}) or {}
                    display_mode = ui_cfg.get("display_mode") or data.get("display_mode")
                    if display_mode:
                        self._set_display_mode(str(display_mode))
            except Exception:
                # ignore YAML hints parsing errors for UI preferences
                pass
        except Exception as exc:
            self._log_script(f"[ERROR] 加载失败: {exc}")

    def _run_script(self) -> None:
        yaml_text = self.yaml_edit.toPlainText().strip()
        if not yaml_text:
            self._log_script("脚本为空，无法运行")
            return
        if self.script_runner and self.script_runner.isRunning():
            self._log_script("脚本正在运行")
            return
        # 进入脚本模式，关闭手动通道避免抢占
        self._switch_to_script_mode()
        self.comm.close()
        self.script_runner = ScriptRunnerQt(yaml_text)
        self.script_runner.sig_log.connect(self._log_script)
        self.script_runner.sig_state.connect(self._update_script_state)
        self.script_runner.sig_progress.connect(self.script_progress.setValue)
        self.script_runner.finished.connect(self._on_script_finished)
        self.script_runner.start()

    def _stop_script(self) -> None:
        if self.script_runner and self.script_runner.isRunning():
            self.script_runner.stop()
            self._log_script("请求停止脚本...")

    def _on_script_finished(self) -> None:
        self._log_script("脚本结束")
        self.script_runner = None
        self._switch_to_manual_mode()

    def _update_script_state(self, state: str) -> None:
        self.script_state_label.setText(f"State: {state}")

    # -------------------- 日志/模式控制 --------------------
    def _log(self, message: str) -> None:
        self.log_signal.emit(message)

    def _append_log(self, message: str) -> None:
        self.log_view.append(message)
        self.log_view.moveCursor(QTextCursor.End)

    def _log_script(self, message: str) -> None:
        self.script_log.append(message)
        self.script_log.moveCursor(QTextCursor.End)

    def _switch_to_script_mode(self) -> None:
        self.mode = "script"
        self.mode_label.setText("Mode: Script")
        # 禁用手动控件
        self.mode_combo.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.close_btn.setEnabled(False)
        self.port_combo.setEnabled(False)
        self.baud_edit.setEnabled(False)
        self.connect_serial_btn.setEnabled(False)
        self.ip_edit.setEnabled(False)
        self.tcp_port_edit.setEnabled(False)
        self.connect_tcp_btn.setEnabled(False)
        self.input_edit.setEnabled(False)
        self.send_btn.setEnabled(False)
        # 脚本按钮状态
        self.run_script_btn.setEnabled(False)
        self.stop_script_btn.setEnabled(True)

    def _switch_to_manual_mode(self) -> None:
        self.mode = "manual"
        self.mode_label.setText("Mode: Manual")
        self.mode_combo.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.close_btn.setEnabled(True)
        self._toggle_manual_comm_mode()
        self.input_edit.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.run_script_btn.setEnabled(True)
        self.stop_script_btn.setEnabled(False)
        self.script_progress.setValue(0)
        self.script_state_label.setText("State: idle")


def run_app(bus: EventBus, comm: CommunicationManager) -> None:
    """便捷启动函数。"""
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow(bus, comm)
    win.show()
    app.exec()
