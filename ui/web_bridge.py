from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

try:
    from PySide6.QtCore import QObject, QTimer, Signal, Slot
except ImportError:  # pragma: no cover
    from PyQt6.QtCore import QObject, QTimer, pyqtSignal as Signal, pyqtSlot as Slot  # type: ignore

from ui.script_runner_qt import ScriptRunnerQt


class WebBridge(QObject):
    """QWebChannel bridge for Web UI."""

    log = Signal(str)
    ui_ready = Signal()
    comm_rx = Signal(object)
    comm_tx = Signal(object)
    comm_status = Signal(object)
    protocol_frame = Signal(object)
    comm_batch = Signal(object)
    script_log = Signal(str)
    script_state = Signal(str)
    script_progress = Signal(int)

    def __init__(self, bus=None, comm=None, window=None) -> None:
        super().__init__()
        self._bus = bus
        self._comm = comm
        self._window = window
        self._script_runner: Optional[ScriptRunnerQt] = None
        self._buffer: List[Dict[str, Any]] = []
        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(50)
        self._flush_timer.timeout.connect(self._flush_buffers)
        self._flush_timer.start()
        if self._bus:
            self._bus.subscribe("comm.rx", self._on_comm_rx)
            self._bus.subscribe("comm.tx", self._on_comm_tx)
            self._bus.subscribe("comm.connected", self._on_comm_status)
            self._bus.subscribe("comm.disconnected", self._on_comm_status)
            self._bus.subscribe("comm.error", self._on_comm_status)
            self._bus.subscribe("protocol.frame", self._on_protocol_frame)

    @Slot(str, result=str)
    def ping(self, message: str) -> str:
        return f"pong: {message}"

    @Slot()
    def notify_ready(self) -> None:
        self.ui_ready.emit()

    @Slot(result="QVariant")
    def list_ports(self) -> list[str]:
        if not self._comm:
            return []
        return self._comm.list_serial_ports()

    @Slot(str, int)
    def connect_serial(self, port: str, baud: int = 115200) -> None:
        if self._comm:
            self._comm.select_serial(port, baud)

    @Slot(str, int)
    def connect_tcp(self, host: str, port: int) -> None:
        if self._comm:
            self._comm.select_tcp(host, port)

    @Slot()
    def disconnect(self) -> None:
        if self._comm:
            self._comm.close()

    @Slot(str)
    def send_text(self, text: str) -> None:
        if self._comm:
            self._comm.send(text.encode())

    @Slot(str)
    def send_hex(self, hex_text: str) -> None:
        if not self._comm:
            return
        try:
            data = bytes.fromhex(hex_text.replace(" ", ""))
        except ValueError:
            self.log.emit("invalid hex string")
            return
        self._comm.send(data)

    @Slot(str)
    def run_script(self, yaml_text: str) -> None:
        if self._script_runner and self._script_runner.isRunning():
            self._script_runner.stop()
            self._script_runner.wait(1000)
        runner = ScriptRunnerQt(yaml_text, bus=self._bus)
        runner.sig_log.connect(self.script_log.emit)
        runner.sig_state.connect(self.script_state.emit)
        runner.sig_progress.connect(self.script_progress.emit)
        self._script_runner = runner
        runner.start()

    @Slot()
    def stop_script(self) -> None:
        if self._script_runner and self._script_runner.isRunning():
            self._script_runner.stop()

    @Slot()
    def window_minimize(self) -> None:
        if self._window:
            self._window.showMinimized()

    @Slot()
    def window_maximize(self) -> None:
        if self._window:
            self._window.showMaximized()

    @Slot()
    def window_restore(self) -> None:
        if self._window:
            self._window.showNormal()

    @Slot()
    def window_toggle_maximize(self) -> None:
        if not self._window:
            return
        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()

    @Slot()
    def window_close(self) -> None:
        if self._window:
            self._window.close()

    @Slot()
    def window_start_move(self) -> None:
        if not self._window:
            return
        handle = self._window.windowHandle()
        if handle and hasattr(handle, "startSystemMove"):
            handle.startSystemMove()

    @Slot(int, int)
    def window_apply_snap(self, screen_x: int, screen_y: int) -> None:
        if not self._window:
            return
        if hasattr(self._window, "_apply_snap"):
            self._window._apply_snap(screen_x, screen_y)

    @Slot(int, int)
    def window_show_system_menu(self, screen_x: int, screen_y: int) -> None:
        if not self._window:
            return
        if hasattr(self._window, "_show_system_menu"):
            self._window._show_system_menu(screen_x, screen_y)

    def _emit_bytes(self, payload: bytes | str | Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(payload, dict):
            return payload
        if isinstance(payload, bytes):
            text = payload.decode(errors="ignore")
            hex_text = payload.hex().upper()
        else:
            text = str(payload)
            hex_text = text.encode().hex().upper()
        return {"text": text, "hex": hex_text, "ts": time.time()}

    def _on_comm_rx(self, payload: Any) -> None:
        self._append_buffer({"kind": "RX", "payload": self._emit_bytes(payload)})

    def _on_comm_tx(self, payload: Any) -> None:
        self._append_buffer({"kind": "TX", "payload": self._emit_bytes(payload)})

    def _on_comm_status(self, payload: Any) -> None:
        self.comm_status.emit({"payload": payload, "ts": time.time()})

    def _on_protocol_frame(self, payload: Any) -> None:
        self._append_buffer({"kind": "FRAME", "payload": payload, "ts": time.time()})

    def _append_buffer(self, item: Dict[str, Any]) -> None:
        self._buffer.append(item)
        if len(self._buffer) > 2000:
            self._buffer = self._buffer[-1000:]

    def _flush_buffers(self) -> None:
        if not self._buffer:
            return
        batch = self._buffer[:]
        self._buffer.clear()
        self.comm_batch.emit(batch)
