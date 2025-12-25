from __future__ import annotations

import importlib
import pkgutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from PySide6.QtCore import QObject, QTimer, Signal, Slot
    from PySide6.QtWidgets import QFileDialog
except ImportError:  # pragma: no cover
    from PyQt6.QtCore import QObject, QTimer, pyqtSignal as Signal, pyqtSlot as Slot  # type: ignore
    from PyQt6.QtWidgets import QFileDialog  # type: ignore

from protocols.registry import ProtocolRegistry
import protocols as protocols_pkg
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
    channel_update = Signal(object)

    def __init__(self, bus=None, comm=None, window=None) -> None:
        super().__init__()
        self._bus = bus
        self._comm = comm
        self._window = window
        self._script_runner: Optional[ScriptRunnerQt] = None
        self._buffer: List[Dict[str, Any]] = []
        self._protocols_loaded = False
        self._channel_state: Dict[str, Any] = {
            "type": None,
            "status": "disconnected",
            "port": None,
            "baud": None,
            "host": None,
            "address": None,
            "error": None,
        }
        self._traffic: Dict[str, int] = {"tx": 0, "rx": 0}
        self._last_channel_emit = 0.0
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

    @Slot(result="QVariant")
    def list_channels(self) -> List[Dict[str, Any]]:
        return self._build_channel_list()

    @Slot(result="QVariant")
    def list_protocols(self) -> List[Dict[str, Any]]:
        self._load_protocols()
        registry = ProtocolRegistry.list()
        items: List[Dict[str, Any]] = []
        for key, cls in sorted(registry.items()):
            doc = (cls.__doc__ or "").strip()
            desc = doc.splitlines()[0].strip() if doc else ""
            category = self._protocol_category(key)
            items.append(
                {
                    "id": key,
                    "key": key,
                    "driver": cls.__name__,
                    "desc": desc,
                    "category": category,
                    "status": "available",
                }
            )
        return items

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

    @Slot(result="QVariant")
    def load_yaml(self) -> Dict[str, str]:
        path, _ = QFileDialog.getOpenFileName(
            None,
            "选择 YAML 脚本",
            str(Path.cwd()),
            "YAML Files (*.yaml *.yml)",
        )
        if not path:
            return {}
        try:
            text = Path(path).read_text(encoding="utf-8")
        except Exception as exc:  # pragma: no cover - UI dialog failure
            self.script_log.emit(f"[ERROR] Load YAML failed: {exc}")
            return {}
        return {"path": path, "name": Path(path).name, "text": text}

    @Slot(str, str, result="QVariant")
    def save_yaml(self, yaml_text: str, suggested_name: str = "workflow.yaml") -> Dict[str, str]:
        if not yaml_text.strip():
            self.script_log.emit("[WARN] YAML is empty, not saved.")
            return {}
        default_path = Path.cwd() / (suggested_name or "workflow.yaml")
        path, _ = QFileDialog.getSaveFileName(
            None,
            "保存 YAML 脚本",
            str(default_path),
            "YAML Files (*.yaml *.yml)",
        )
        if not path:
            return {}
        try:
            Path(path).write_text(yaml_text, encoding="utf-8")
        except Exception as exc:  # pragma: no cover - UI dialog failure
            self.script_log.emit(f"[ERROR] Save YAML failed: {exc}")
            return {}
        return {"path": path, "name": Path(path).name}

    @Slot()
    def window_minimize(self) -> None:
        if self._window:
            self._window.showMinimized()

    @Slot()
    def window_maximize(self) -> None:
        if self._window:
            if hasattr(self._window, "_remember_normal_geometry"):
                self._window._remember_normal_geometry()
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
            if hasattr(self._window, "_remember_normal_geometry"):
                self._window._remember_normal_geometry()
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
    def window_start_move_at(self, screen_x: int, screen_y: int) -> None:
        if not self._window:
            return
        if hasattr(self._window, "_start_move"):
            self._window._start_move(screen_x, screen_y)
            return
        handle = self._window.windowHandle()
        if handle and hasattr(handle, "startSystemMove"):
            handle.startSystemMove()

    @Slot(str)
    def window_start_resize(self, edge: str) -> None:
        if not self._window:
            return
        if hasattr(self._window, "_start_resize"):
            self._window._start_resize(edge)

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

    def _build_channel_list(self) -> List[Dict[str, Any]]:
        if not self._channel_state.get("type"):
            return []
        info = dict(self._channel_state)
        channel_type = "serial" if info["type"] == "serial" else "tcp-client"
        channel_id = info.get("address") or info.get("port") or channel_type
        return [
            {
                "id": f"{channel_type}:{channel_id}",
                "type": channel_type,
                "status": info.get("status") or "disconnected",
                "port": info.get("port"),
                "baud": info.get("baud"),
                "host": info.get("host"),
                "address": info.get("address"),
                "error": info.get("error") or "",
                "tx_bytes": self._traffic.get("tx", 0),
                "rx_bytes": self._traffic.get("rx", 0),
            }
        ]

    def _emit_channel_update(self, force: bool = False) -> None:
        now = time.time()
        if not force and now - self._last_channel_emit < 0.5:
            return
        self._last_channel_emit = now
        self.channel_update.emit(self._build_channel_list())

    def _on_comm_rx(self, payload: Any) -> None:
        if isinstance(payload, (bytes, bytearray)):
            self._traffic["rx"] += len(payload)
        self._append_buffer({"kind": "RX", "payload": self._emit_bytes(payload)})
        self._emit_channel_update()

    def _on_comm_tx(self, payload: Any) -> None:
        if isinstance(payload, (bytes, bytearray)):
            self._traffic["tx"] += len(payload)
        self._append_buffer({"kind": "TX", "payload": self._emit_bytes(payload)})
        self._emit_channel_update()

    def _on_comm_status(self, payload: Any) -> None:
        if payload is None:
            self._channel_state["status"] = "disconnected"
        elif isinstance(payload, str):
            self._channel_state["status"] = "error"
            self._channel_state["error"] = payload
        elif isinstance(payload, dict):
            self._channel_state["type"] = payload.get("type")
            self._channel_state["port"] = payload.get("port")
            self._channel_state["baud"] = payload.get("baud")
            self._channel_state["host"] = payload.get("host")
            self._channel_state["address"] = payload.get("address")
            self._channel_state["status"] = "connected"
            self._channel_state["error"] = None
            self._traffic = {"tx": 0, "rx": 0}
        self.comm_status.emit({"payload": payload, "ts": time.time()})
        self._emit_channel_update(force=True)

    def _on_protocol_frame(self, payload: Any) -> None:
        self._append_buffer({"kind": "FRAME", "payload": payload, "ts": time.time()})

    def _load_protocols(self) -> None:
        if self._protocols_loaded:
            return
        self._protocols_loaded = True
        try:
            for module in pkgutil.iter_modules(protocols_pkg.__path__):
                importlib.import_module(f"{protocols_pkg.__name__}.{module.name}")
        except Exception as exc:  # pragma: no cover - optional UI detail
            self.log.emit(f"[WARN] Load protocols failed: {exc}")

    @staticmethod
    def _protocol_category(key: str) -> str:
        name = (key or "").lower()
        if name.startswith("modbus_"):
            return "modbus"
        if "tcp" in name:
            return "tcp"
        return "custom"

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
