"""通信管理器：统一封装串口与 TCP，会话事件转发到 comm.* 通道。"""

from __future__ import annotations

from typing import Optional, Union

from core.event_bus import EventBus
from core.serial_manager import SerialManager
from core.tcp_session import TcpSession

SessionType = Union[SerialManager, TcpSession]


class CommunicationManager:
    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._current_session: Optional[SessionType] = None

        # 事件转发：底层 -> comm.*
        self._bus.subscribe("serial.rx", lambda data: self._bus.publish("comm.rx", data))
        self._bus.subscribe("tcp.rx", lambda data: self._bus.publish("comm.rx", data))

        self._bus.subscribe("serial.tx", lambda data: self._bus.publish("comm.tx", data))
        self._bus.subscribe("tcp.tx", lambda data: self._bus.publish("comm.tx", data))

        self._bus.subscribe(
            "serial.error", lambda reason: self._bus.publish("comm.error", reason)
        )
        self._bus.subscribe("tcp.error", lambda reason: self._bus.publish("comm.error", reason))
        # 协议帧请求发送 -> 调用当前会话发送
        self._bus.subscribe("protocol.tx", self._handle_protocol_tx)

    def select_serial(self, port: str, baud: int) -> None:
        """选择串口通道并连接。"""
        self.close()
        session = SerialManager(self._bus)
        session.open(port=port, baudrate=baud)
        self._current_session = session
        self._bus.publish("comm.connected", {"type": "serial", "port": port})

    def select_tcp(self, ip: str, port: int) -> None:
        """选择 TCP 通道并连接。"""
        self.close()
        session = TcpSession(self._bus)
        session.connect(ip, port)
        self._current_session = session
        self._bus.publish("comm.connected", {"type": "tcp", "address": f"{ip}:{port}"})

    def close(self) -> None:
        """关闭当前会话。"""
        if self._current_session:
            try:
                self._current_session.close()
            except Exception:
                pass
            self._current_session = None
            self._bus.publish("comm.disconnected")

    def send(self, data: bytes) -> None:
        """通过当前会话发送数据。"""
        if not self._current_session:
            self._bus.publish("comm.error", "no active session")
            return
        try:
            self._current_session.send(data)
        except Exception as exc:
            self._bus.publish("comm.error", str(exc))

    def list_serial_ports(self) -> list[str]:
        """返回可用串口列表，供 UI 使用。"""
        return SerialManager.list_ports()

    def _handle_protocol_tx(self, data: bytes) -> None:
        """处理协议层构造好的帧并发送。"""
        if not data:
            return
        self.send(data)
