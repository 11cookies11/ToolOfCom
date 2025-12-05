"""串口管理：负责数据收发，与 EventBus 解耦，不包含协议解析。"""

from __future__ import annotations

import threading
import time
from typing import Any, List, Optional

import serial
from serial import SerialException
from serial.tools import list_ports

from core.event_bus import EventBus


class SerialManager:
    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self._ser: Optional[serial.Serial] = None
        self._rx_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.RLock()
        self._port: Optional[str] = None
        self._baudrate: Optional[int] = None

    @staticmethod
    def list_ports() -> List[str]:
        """返回系统可用串口列表。"""
        return [port.device for port in list_ports.comports()]

    def open(self, port: str, baudrate: int) -> None:
        """打开串口并启动接收线程。"""
        with self._lock:
            self._port, self._baudrate = port, baudrate
            if self._ser and self._ser.is_open:
                self.close()
            try:
                self._ser = serial.Serial(port=port, baudrate=baudrate, timeout=0.1)
                self._running = True
                self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
                self._rx_thread.start()
                self._log(f"串口打开: {port} @ {baudrate}")
                self.bus.publish("serial.opened", port)
            except SerialException as exc:
                self._log(f"[ERROR] 打开串口失败: {exc}")
                self.bus.publish("serial.error", str(exc))

    def close(self) -> None:
        """关闭串口并停止接收线程。"""
        with self._lock:
            self._running = False
            if self._rx_thread and self._rx_thread.is_alive():
                self._rx_thread.join(timeout=1)
            if self._ser:
                try:
                    self._ser.close()
                except Exception:
                    pass
                self._ser = None
            self._log("串口关闭")
            self.bus.publish("serial.closed")

    def send(self, data: bytes) -> None:
        """发送数据并发布发送事件。"""
        with self._lock:
            ser = self._ser
        if not ser or not ser.is_open:
            self._log("[WARN] 串口未打开，发送忽略")
            return
        try:
            ser.write(data)
            self._log(f"串口发送 {len(data)} bytes")
            self.bus.publish("serial.tx", data)
        except SerialException as exc:
            self._log(f"[ERROR] 发送失败: {exc}")
            self.bus.publish("serial.error", str(exc))

    def _rx_loop(self) -> None:
        """接收线程：非阻塞读取，异常时尝试自动重连。"""
        while self._running:
            ser = self._ser
            if not ser:
                time.sleep(0.1)
                continue

            try:
                if not ser.is_open:
                    raise SerialException("串口未打开")

                waiting = ser.in_waiting or 0
                if waiting == 0:
                    # 轻量 sleep，避免空转占用 CPU
                    time.sleep(0.02)
                    continue

                data = ser.read(waiting)
                if data:
                    self.bus.publish("serial.rx", data)
            except SerialException as exc:
                self._log(f"[ERROR] 接收异常: {exc}")
                self.bus.publish("serial.error", str(exc))
                self._attempt_reconnect()
            except Exception as exc:
                # 防止线程崩溃
                self._log(f"[ERROR] 未知接收异常: {exc}")
                self.bus.publish("serial.error", str(exc))
                time.sleep(0.1)

    def _attempt_reconnect(self) -> None:
        """自动重连，不阻塞关闭操作。"""
        if not self._running:
            return

        port, baudrate = self._port, self._baudrate
        if not port or not baudrate:
            return

        self._log(f"尝试重连串口: {port}")
        while self._running:
            try:
                with self._lock:
                    if self._ser and self._ser.is_open:
                        return
                    self._ser = serial.Serial(port=port, baudrate=baudrate, timeout=0.1)
                self._log(f"重连成功: {port}")
                self.bus.publish("serial.opened", port)
                return
            except SerialException as exc:
                self._log(f"[WARN] 重连失败: {exc}")
                self.bus.publish("serial.error", f"reconnect failed: {exc}")
                time.sleep(1)

    @staticmethod
    def _log(msg: str) -> None:
        # 简易日志，后续可换成 loguru/logging
        print(f"[SerialManager] {msg}")
