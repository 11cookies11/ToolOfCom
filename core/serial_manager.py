"""串口管理占位：负责打开/关闭端口、发送接收等。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class SerialConfig:
    port: str
    baudrate: int = 115200
    bytesize: int = 8
    parity: str = "N"
    stopbits: float = 1
    timeout: float = 0.5


class SerialManager:
    def __init__(self, config: SerialConfig) -> None:
        self.config = config
        self._ser = None  # 可接入 pyserial.Serial

    def open(self) -> None:
        # TODO: 实现 pyserial 串口打开
        pass

    def close(self) -> None:
        # TODO: 实现串口关闭
        pass

    def send(self, data: bytes) -> None:
        # TODO: 写入串口
        pass

    def read(self, size: Optional[int] = None) -> bytes:
        # TODO: 读取串口
        return b""
