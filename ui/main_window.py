"""Qt 主窗口：通信控制台 + 脚本运行（浅色主题，简体中文 UI）。"""

from __future__ import annotations

import sys
import binascii
import codecs
from pathlib import Path
from typing import List, Optional

import yaml

try:
    from PySide6.QtCore import Qt, Signal
    from PySide6.QtGui import QTextCursor
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QFormLayout,
        QFrame,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QFileDialog,
        QLineEdit,
        QMainWindow,
        QPlainTextEdit,
        QProgressBar,
        QPushButton,
        QSplitter,
        QStackedWidget,
        QTabWidget,
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
        QFormLayout,
        QFrame,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QFileDialog,
        QLineEdit,
        QMainWindow,
        QPlainTextEdit,
        QProgressBar,
        QPushButton,
        QSplitter,
        QStackedWidget,
        QTabWidget,
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
        self.setWindowTitle("TOC 控制台")
        self.resize(1320, 860)
        self.setMinimumSize(960, 600)
        # 无边框窗口，自定义标题栏（按钮在内容区）
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)

        self._build_ui()
        self._wire_events()
        self._refresh_ports()
        self._toggle_manual_comm_mode()

    # -------------------- UI 构建 --------------------
    def _build_ui(self) -> None:
        self._apply_light_theme()

        # 顶部控制条
        self.mode_label = QLabel("模式：手动")
        self.run_script_btn = QPushButton("运行脚本")
        self.stop_script_btn = QPushButton("停止脚本")
        self.stop_script_btn.setEnabled(False)
        self.load_yaml_btn = QPushButton("加载 YAML")
        self.save_yaml_btn = QPushButton("保存 YAML")

        top_bar = QHBoxLayout()
        top_bar.addWidget(self.mode_label)
        top_bar.addStretch()

        # 左侧导航（标题在外，按钮在圆角面板内）
        self.nav_buttons: dict[str, QPushButton] = {}
        nav_frame = QFrame()
        nav_frame.setObjectName("navFrame")
        nav_layout = QVBoxLayout(nav_frame)
        nav_items = [
            ("手动调试", "control"),
            ("自动脚本", "scripts"),
            ("通道管理", "channels"),
            ("协议驱动", "protocols"),
        ]
        for label, key in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _=False, k=key: self._on_nav_clicked(k))
            nav_layout.addWidget(btn)
            self.nav_buttons[key] = btn
        nav_layout.addStretch()

        nav_container = QVBoxLayout()
        nav_title = QLabel("导航")
        nav_title.setObjectName("sectionTitle")
        nav_container.addWidget(nav_title)
        nav_container.addWidget(nav_frame)

        # 控制面板（通道/发送）供“手动调试”视图使用，标题放在外部
        properties_frame = QFrame()
        properties_frame.setObjectName("panel")
        properties_layout = QVBoxLayout(properties_frame)

        channel_group = QGroupBox("通道与连接")
        channel_form = QFormLayout(channel_group)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["串口", "TCP"])
        self.refresh_btn = QPushButton("刷新")
        self.close_btn = QPushButton("关闭连接")
        channel_form.addRow("模式", self.mode_combo)
        channel_form.addRow("刷新", self.refresh_btn)
        channel_form.addRow("关闭", self.close_btn)

        self.serial_row = QWidget()
        serial_layout = QHBoxLayout(self.serial_row)
        serial_layout.setContentsMargins(0, 0, 0, 0)
        self.port_combo = QComboBox()
        self.baud_edit = QLineEdit("115200")
        self.connect_serial_btn = QPushButton("连接串口")
        serial_layout.addWidget(self.port_combo, 2)
        serial_layout.addWidget(self.baud_edit, 1)
        serial_layout.addWidget(self.connect_serial_btn, 1)
        self.serial_label = QLabel("串口")
        channel_form.addRow(self.serial_label, self.serial_row)

        self.tcp_row = QWidget()
        tcp_layout = QHBoxLayout(self.tcp_row)
        tcp_layout.setContentsMargins(0, 0, 0, 0)
        self.ip_edit = QLineEdit("127.0.0.1")
        self.tcp_port_edit = QLineEdit("6000")
        self.connect_tcp_btn = QPushButton("连接 TCP")
        tcp_layout.addWidget(self.ip_edit, 2)
        tcp_layout.addWidget(self.tcp_port_edit, 1)
        tcp_layout.addWidget(self.connect_tcp_btn, 1)
        self.tcp_label = QLabel("TCP")
        channel_form.addRow(self.tcp_label, self.tcp_row)

        properties_layout.addWidget(channel_group)

        manual_group = QGroupBox("手动发送")
        manual_layout = QVBoxLayout(manual_group)
        display_row = QWidget()
        display_layout = QHBoxLayout(display_row)
        display_layout.setContentsMargins(0, 0, 0, 0)
        self.display_combo = QComboBox()
        self.display_combo.addItems(["HEX", "Text"])
        display_layout.addWidget(QLabel("显示格式"))
        display_layout.addWidget(self.display_combo)
        display_layout.addStretch()
        manual_layout.addWidget(display_row)

        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("输入 HEX（如：55 AA 01）")
        self.send_btn = QPushButton("发送")
        send_row = QHBoxLayout()
        send_row.addWidget(self.input_edit, 3)
        send_row.addWidget(self.send_btn, 1)
        manual_layout.addLayout(send_row)

        properties_layout.addWidget(manual_group)

        properties_layout.addStretch()

        # 中部内容：通道 / 协议 / 控制（控制时主区显示日志，右区显示面板）
        channels_tab = self._build_channels_tab()
        protocols_tab = self._build_protocols_tab()

        # 底部日志
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.script_log = QTextEdit()
        self.script_log.setReadOnly(True)
        self.uart_log = QTextEdit()
        self.uart_log.setReadOnly(True)
        self.tcp_log = QTextEdit()
        self.tcp_log.setReadOnly(True)
        for view in (self.log_view, self.script_log, self.uart_log, self.tcp_log):
            view.setMinimumHeight(220)
            view.setStyleSheet("font-family: Consolas, 'SF Mono', 'JetBrains Mono', monospace; font-size: 12px;")

        # 日志过滤条
        log_filter_bar = QHBoxLayout()
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["ALL", "INFO", "WARN", "ERROR"])
        self.log_search_edit = QLineEdit()
        self.log_search_edit.setPlaceholderText("搜索日志内容...")
        self.log_search_edit.setObjectName("logSearch")
        self.log_filter_btn = QPushButton("过滤")
        self.log_reset_btn = QPushButton("重置")
        log_filter_bar.addWidget(QLabel("级别"))
        log_filter_bar.addWidget(self.log_level_combo)
        log_filter_bar.addWidget(QLabel("关键字"))
        log_filter_bar.addWidget(self.log_search_edit, 1)
        log_filter_bar.addWidget(self.log_filter_btn)
        log_filter_bar.addWidget(self.log_reset_btn)

        log_tabs = QTabWidget()
        log_tabs.addTab(self.log_view, "控制台")
        log_tabs.addTab(self.uart_log, "UART")
        log_tabs.addTab(self.tcp_log, "TCP")
        log_tabs.addTab(self.script_log, "脚本")

        # 主分割：左（导航+内容），右（日志终端）
        log_panel = QVBoxLayout()
        log_panel.addLayout(log_filter_bar)
        log_panel.addWidget(log_tabs)

        self.log_container = QWidget()
        self.log_container.setLayout(log_panel)

        # 控制视图：上部通信收发+控制面板，底部日志（与脚本视图一致的控制台）
        self.comm_display = QTextEdit()
        self.comm_display.setReadOnly(True)
        self.comm_display.setPlaceholderText("通信收发显示（UART/TCP）")
        self.comm_display.setMinimumHeight(180)
        self.comm_display.setStyleSheet("font-family: Consolas, 'SF Mono', 'JetBrains Mono', monospace; font-size: 12px;")

        display_frame = QFrame()
        display_frame.setObjectName("panel")
        display_layout = QVBoxLayout(display_frame)
        display_layout.addWidget(self.comm_display)

        display_container = QWidget()
        display_container_layout = QVBoxLayout(display_container)
        display_title = QLabel("通信收发")
        display_title.setObjectName("sectionTitle")
        display_container_layout.addWidget(display_title)
        display_container_layout.addWidget(display_frame)

        control_container = QWidget()
        control_container_layout = QVBoxLayout(control_container)
        control_title = QLabel("控制与连接")
        control_title.setObjectName("sectionTitle")
        control_container_layout.addWidget(control_title)
        control_container_layout.addWidget(properties_frame)

        control_top = QSplitter(Qt.Horizontal)
        control_top.addWidget(display_container)
        control_top.addWidget(control_container)
        control_top.setStretchFactor(0, 1)
        control_top.setStretchFactor(1, 0)
        control_top.setSizes([960, 360])

        self.control_log_host = QWidget()
        self.control_log_host.setLayout(QVBoxLayout())
        self.control_log_host.layout().setContentsMargins(0, 0, 0, 0)
        self.control_log_host.layout().addWidget(self.log_container)

        control_view = QSplitter(Qt.Vertical)
        control_view.addWidget(control_top)
        control_view.addWidget(self.control_log_host)
        control_view.setStretchFactor(0, 1)
        control_view.setStretchFactor(1, 0)
        control_view.setSizes([520, 320])

        # 脚本/YAML 视图：顶部左右分区，底部日志
        self.yaml_edit = QPlainTextEdit()
        self.yaml_edit.setPlaceholderText("在此粘贴或编辑 YAML，或点击“加载 YAML”载入文件")

        editor_frame = QFrame()
        editor_frame.setObjectName("panel")
        editor_layout = QVBoxLayout(editor_frame)
        editor_layout.addWidget(self.yaml_edit)

        editor_container = QWidget()
        editor_container_layout = QVBoxLayout(editor_container)
        editor_title = QLabel("自动脚本编辑")
        editor_title.setObjectName("sectionTitle")
        editor_container_layout.addWidget(editor_title)
        editor_container_layout.addWidget(editor_frame)

        script_actions = QFrame()
        script_actions.setObjectName("panel")
        actions_layout = QVBoxLayout(script_actions)

        script_btn_row = QHBoxLayout()
        script_btn_row.addWidget(self.load_yaml_btn)
        script_btn_row.addWidget(self.save_yaml_btn)
        script_btn_row.addWidget(self.run_script_btn)
        script_btn_row.addWidget(self.stop_script_btn)
        actions_layout.addLayout(script_btn_row)

        self.script_state_label = QLabel("状态：空闲")
        self.script_progress = QProgressBar()
        self.script_progress.setRange(0, 100)
        actions_layout.addWidget(self.script_state_label)
        actions_layout.addWidget(self.script_progress)
        actions_layout.addStretch()

        actions_container = QWidget()
        actions_container_layout = QVBoxLayout(actions_container)
        actions_title = QLabel("自动脚本控制")
        actions_title.setObjectName("sectionTitle")
        actions_container_layout.addWidget(actions_title)
        actions_container_layout.addWidget(script_actions)

        script_top = QSplitter(Qt.Horizontal)
        script_top.addWidget(editor_container)
        script_top.addWidget(actions_container)
        script_top.setStretchFactor(0, 1)
        script_top.setStretchFactor(1, 0)
        script_top.setSizes([1100, 240])

        self.script_log_host = QWidget()
        self.script_log_host.setLayout(QVBoxLayout())
        self.script_log_host.layout().setContentsMargins(0, 0, 0, 0)

        script_view = QSplitter(Qt.Vertical)
        script_view.addWidget(script_top)
        script_view.addWidget(self.script_log_host)
        script_view.setStretchFactor(0, 1)
        script_view.setStretchFactor(1, 0)
        script_view.setSizes([520, 340])

        self.main_stack = QStackedWidget()
        self.stack_indices = {
            "channels": self.main_stack.addWidget(channels_tab),
            "protocols": self.main_stack.addWidget(protocols_tab),
            "control_view": self.main_stack.addWidget(control_view),
            "scripts": self.main_stack.addWidget(script_view),
        }

        # 左侧容器包含标题与导航面板
        nav_widget = QWidget()
        nav_widget.setLayout(nav_container)

        main_split = QSplitter(Qt.Horizontal)
        main_split.addWidget(nav_widget)
        main_split.addWidget(self.main_stack)
        main_split.setStretchFactor(0, 0)
        main_split.setStretchFactor(1, 1)
        main_split.setSizes([180, 1260])

        layout = QVBoxLayout()
        layout.addLayout(top_bar)
        layout.addWidget(main_split, 1)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.log_signal.connect(self._append_log)
        # 默认选中控制面板
        self._select_nav("control")
        self._apply_layout_for("control")

    def _apply_light_theme(self) -> None:
        # 清爽浅色 + 青色点缀
        self.setStyleSheet(
            """
            QWidget { background: #f6f8fb; color: #1b2333; font-size: 13px; }
            QFrame#navFrame { background: #eef1f6; border: 1px solid #d8deea; border-radius: 8px; }
            QFrame#panel { background: #ffffff; border: 1px solid #d8deea; border-radius: 10px; }
            QFrame#card { background: #ffffff; border: 1px solid #d8deea; border-radius: 10px; padding: 10px; }
            QLabel#sectionTitle { color: #00a6c2; font-weight: 600; }
            QPushButton { background: #e7edf7; border: 1px solid #cfd8e8; padding: 6px 10px; border-radius: 6px; }
            QPushButton:hover { border-color: #00bcd4; color: #0088a1; }
            QPushButton:pressed { background: #d9e2f0; }
            QPushButton#navButton { text-align: left; padding: 8px 10px; }
            QPushButton#navButton:checked { background: #d9e2f0; border-color: #00a6c2; color: #006e82; }
            QLineEdit, QPlainTextEdit, QTextEdit, QComboBox { background: #ffffff; border: 1px solid #cfd8e8; border-radius: 6px; padding: 6px; selection-background-color: #00bcd4; }
            QTabWidget::pane { border: 1px solid #d8deea; }
            QTabBar::tab { background: #eef1f6; padding: 6px 10px; border: 1px solid #d8deea; border-bottom: none; }
            QTabBar::tab:selected { background: #ffffff; color: #0088a1; }
            QProgressBar { background: #eef1f6; border: 1px solid #d8deea; border-radius: 6px; text-align: center; }
            QProgressBar::chunk { background-color: #00bcd4; border-radius: 6px; }
            QListWidget { background: #ffffff; border: 1px solid #cfd8e8; border-radius: 6px; }
            QLineEdit#logSearch { padding-left: 10px; }
            """
        )

    # -------------------- 辅助视图 --------------------
    def _create_status_label(self, text: str, color: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(
            f"color: #ffffff; background: {color}; padding: 2px 10px; border-radius: 10px; font-weight: 600;"
        )
        return label

    def _add_card(self, parent_layout: QVBoxLayout, title: str, status: str, status_color: str, lines: List[str]) -> None:
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        header = QHBoxLayout()
        header.addWidget(QLabel(title))
        header.addStretch()
        header.addWidget(self._create_status_label(status, status_color))
        card_layout.addLayout(header)
        for line in lines:
            card_layout.addWidget(QLabel(line))
        parent_layout.addWidget(card)

    def _create_divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: #d8deea;")
        return line

    def _build_channels_tab(self) -> QWidget:
        tab = QWidget()
        outer = QVBoxLayout(tab)
        title = QLabel("通道列表")
        title.setObjectName("sectionTitle")
        outer.addWidget(title)

        frame = QFrame()
        frame.setObjectName("panel")
        layout = QVBoxLayout(frame)
        self._add_card(
            layout,
            "UART 通道",
            "已连接",
            "#4cc38a",
            [
                "类型：串口",
                "端口：COM3",
                "波特率：115200",
                "标签：boot, debug",
            ],
        )
        self._add_card(
            layout,
            "TCP 通道",
            "未连接",
            "#f5a524",
            [
                "类型：TCP",
                "地址：192.168.1.100:4321",
                "标签：bridge, test",
            ],
        )
        layout.addStretch()
        outer.addWidget(frame)
        return tab

    def _build_protocols_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        title = QLabel("协议驱动")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        self._add_card(
            layout,
            "XMODEM 驱动",
            "启用",
            "#4cc38a",
            [
                "特性：CRC、块重传、EOT",
                "用途：固件写入/升级",
            ],
        )
        self._add_card(
            layout,
            "Modbus 驱动",
            "可用",
            "#4cc38a",
            [
                "特性：读写寄存器/线圈",
                "用途：设备调试与监控",
            ],
        )
        self._add_card(
            layout,
            "自定义驱动",
            "未配置",
            "#f14d50",
            [
                "特性：用户扩展",
                "用途：按需加载自定义协议",
            ],
        )
        layout.addStretch()
        return tab

    # -------------------- 事件绑定 --------------------
    def _wire_events(self) -> None:
        self.refresh_btn.clicked.connect(self._refresh_ports)
        self.mode_combo.currentIndexChanged.connect(self._toggle_manual_comm_mode)
        self.close_btn.clicked.connect(self._close_comm)
        self.connect_serial_btn.clicked.connect(self._connect_serial)
        self.connect_tcp_btn.clicked.connect(self._connect_tcp)
        self.send_btn.clicked.connect(self._send_data)
        self.display_combo.currentIndexChanged.connect(self._change_display_mode)
        self.log_filter_btn.clicked.connect(self._apply_log_filter)
        self.log_reset_btn.clicked.connect(self._reset_log_filter)

        self.load_yaml_btn.clicked.connect(self._load_yaml_file)
        self.save_yaml_btn.clicked.connect(self._save_yaml_file)
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
        self._log(f"检测到串口: {ports}" if ports else "未检测到可用串口")

    def _toggle_manual_comm_mode(self) -> None:
        is_serial = self.mode_combo.currentText() == "串口"
        serial_enabled = is_serial and self.mode == "manual"
        tcp_enabled = (not is_serial) and self.mode == "manual"
        self.port_combo.setEnabled(serial_enabled)
        self.baud_edit.setEnabled(serial_enabled)
        self.connect_serial_btn.setEnabled(serial_enabled)
        self.ip_edit.setEnabled(tcp_enabled)
        self.tcp_port_edit.setEnabled(tcp_enabled)
        self.connect_tcp_btn.setEnabled(tcp_enabled)
        # 显示当前模式对应的行，隐藏另一行
        self.serial_row.setVisible(is_serial)
        self.tcp_row.setVisible(not is_serial)
        self.serial_label.setVisible(is_serial)
        self.tcp_label.setVisible(not is_serial)

    def _change_display_mode(self) -> None:
        self.display_mode = self.display_combo.currentText().lower()
        self._text_decoder = codecs.getincrementaldecoder("utf-8")()
        self._rx_text_buffer = ""
        if self.display_mode == "hex":
            self.input_edit.setPlaceholderText("输入 HEX（如：55 AA 01）")
        else:
            self.input_edit.setPlaceholderText("输入 UTF-8 文本")

    def _set_display_mode(self, mode: str) -> None:
        mode = (mode or "").lower()
        if mode not in {"hex", "text"}:
            return
        target_text = "HEX" if mode == "hex" else "Text"
        if self.display_combo.currentText().lower() == mode:
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
                self._log("HEX 格式错误，示例：55 AA 01")
            else:
                self._log("文本编码错误，请输入 UTF-8 文本")
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
            self._log("TCP 端口格式错误")
            return
        self.comm.select_tcp(ip, port)

    # -------------------- 脚本集成 --------------------
    def _load_yaml_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 YAML 脚本", str(Path.cwd()), "YAML Files (*.yaml *.yml)"
        )
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8")
            self.yaml_edit.setPlainText(text)
            self._log_script(f"已加载脚本: {path}")
            try:
                data = yaml.safe_load(text) or {}
                if isinstance(data, dict):
                    ui_cfg = data.get("ui", {}) or {}
                    display_mode = ui_cfg.get("display_mode") or data.get("display_mode")
                    if display_mode:
                        self._set_display_mode(str(display_mode))
            except Exception:
                pass
        except Exception as exc:
            self._log_script(f"[ERROR] 加载失败: {exc}")

    def _save_yaml_file(self) -> None:
        text = self.yaml_edit.toPlainText()
        if not text.strip():
            self._log_script("YAML 为空，未保存")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存 YAML 脚本", str(Path.cwd() / "workflow.yaml"), "YAML Files (*.yaml *.yml)"
        )
        if not path:
            return
        try:
            Path(path).write_text(text, encoding="utf-8")
            self._log_script(f"已保存脚本: {path}")
        except Exception as exc:
            self._log_script(f"[ERROR] 保存失败: {exc}")

    def _run_script(self) -> None:
        yaml_text = self.yaml_edit.toPlainText().strip()
        if not yaml_text:
            self._log_script("脚本为空，无法运行")
            return
        if self.script_runner and self.script_runner.isRunning():
            self._log_script("脚本正在运行中")
            return
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
            self._log_script("正在请求停止脚本...")

    def _on_script_finished(self) -> None:
        self._log_script("脚本结束")
        self.script_runner = None
        self._switch_to_manual_mode()

    def _update_script_state(self, state: str) -> None:
        self.script_state_label.setText(f"状态：{state}")

    # -------------------- 日志/模式控制 --------------------
    def _log(self, message: str) -> None:
        # 控制台日志存储，便于过滤
        if not hasattr(self, "_console_logs"):
            self._console_logs: List[str] = []
        self._console_logs.append(str(message))
        self.log_signal.emit(message)

    def _append_log(self, message: str) -> None:
        # 将日志同步到控制台与通道 Tab；后续可按通道拆分。
        self.log_view.append(message)
        self.log_view.moveCursor(QTextCursor.End)
        self.uart_log.append(message)
        self.uart_log.moveCursor(QTextCursor.End)
        self.tcp_log.append(message)
        self.tcp_log.moveCursor(QTextCursor.End)
        if hasattr(self, "comm_display"):
            self.comm_display.append(message)
            self.comm_display.moveCursor(QTextCursor.End)

    def _log_script(self, message: str) -> None:
        self.script_log.append(message)
        self.script_log.moveCursor(QTextCursor.End)

    def _apply_log_filter(self) -> None:
        keyword = (self.log_search_edit.text() or "").strip().lower()
        level = self.log_level_combo.currentText()
        logs = getattr(self, "_console_logs", [])
        filtered: List[str] = []
        for line in logs:
            if keyword and keyword not in line.lower():
                continue
            if level != "ALL":
                if level == "ERROR" and "[ERROR]" not in line:
                    continue
                if level == "WARN" and "[WARN]" not in line:
                    continue
                if level == "INFO" and any(tag in line for tag in ["[WARN]", "[ERROR]"]):
                    # 简单排除警告/错误；其他视为 INFO
                    continue
            filtered.append(line)
        self.log_view.clear()
        self.log_view.append("\n".join(filtered))

    def _reset_log_filter(self) -> None:
        self.log_search_edit.clear()
        self.log_level_combo.setCurrentIndex(0)
        self.log_view.clear()
        for line in getattr(self, "_console_logs", []):
            self.log_view.append(line)

    def _switch_to_script_mode(self) -> None:
        self.mode = "script"
        self.mode_label.setText("模式：脚本")
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
        self.run_script_btn.setEnabled(False)
        self.stop_script_btn.setEnabled(True)

    def _switch_to_manual_mode(self) -> None:
        self.mode = "manual"

    # -------------------- 窗口拖拽（无边框） --------------------
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            gp = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
            self._drag_pos = gp - self.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.LeftButton and hasattr(self, "_drag_pos"):
            gp = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
            self.move(gp - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and hasattr(self, "_drag_pos"):
            self._drag_pos = None
            event.accept()
        super().mouseReleaseEvent(event)
        self.mode_label.setText("模式：手动")
        self.mode_combo.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.close_btn.setEnabled(True)
        self._toggle_manual_comm_mode()
        self.input_edit.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.run_script_btn.setEnabled(True)
        self.stop_script_btn.setEnabled(False)
        self.script_progress.setValue(0)
        self.script_state_label.setText("状态：空闲")

    # -------------------- 导航与标签同步 --------------------
    def _on_nav_clicked(self, key: str) -> None:
        self._apply_layout_for(key)
        self._select_nav(key)

    def _select_nav(self, key: str) -> None:
        for k, btn in self.nav_buttons.items():
            btn.setChecked(k == key)

    def _apply_layout_for(self, key: str) -> None:
        if key == "channels":
            self.main_stack.setCurrentIndex(self.stack_indices["channels"])
        elif key == "protocols":
            self.main_stack.setCurrentIndex(self.stack_indices["protocols"])
        elif key == "control":
            self.main_stack.setCurrentIndex(self.stack_indices["control_view"])
            self._mount_log_to(self.control_log_host)
        elif key == "scripts":
            self.main_stack.setCurrentIndex(self.stack_indices["scripts"])
            self._mount_log_to(self.script_log_host)
        else:
            self.main_stack.setCurrentIndex(self.stack_indices["channels"])
            self._mount_log_to(self.control_log_host)

    def _mount_log_to(self, host: QWidget) -> None:
        if not hasattr(self, "log_container"):
            return
        # 移除旧父级
        self.log_container.setParent(None)
        layout = host.layout()
        if layout is None:
            layout = QVBoxLayout(host)
        # 清空旧子控件
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        layout.addWidget(self.log_container)

def run_app(bus: EventBus, comm: CommunicationManager) -> None:
    """启动 Qt 窗口的便捷函数。"""
    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow(bus, comm)
    win.show()
    app.exec()
