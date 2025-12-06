from __future__ import annotations

import time
from pathlib import Path

from protocols.base import BaseProtocol
from protocols.registry import ProtocolRegistry
from utils.crc16 import crc16_xmodem


SOH = 0x01
STX = 0x02
EOT = 0x04
ACK = 0x06
NAK = 0x15
CAN = 0x18
CRC_REQ = 0x43  # 'C'


class YModem(BaseProtocol):
    """YMODEM 文件发送（1024 字节帧 + 文件名）。"""

    def execute(self, file_path: str, retries: int = 10, start_timeout: float = 10.0):
        path = Path(file_path)
        data = path.read_bytes()
        file_name = path.name
        file_size = len(data)

        self._wait_start(start_timeout)

        header_payload = f"{file_name}\0{file_size}\0".encode("ascii", errors="ignore")
        header_block = self._make_packet(0, header_payload, use_1k=True)
        if not self._send_with_ack(header_block, retries):
            raise TimeoutError("YMODEM 头块发送失败")

        # 接收端通常会再发一次 'C' 提示继续
        _ = self.channel.read(1, timeout=1.0)

        block_no = 1
        offset = 0
        while offset < len(data):
            chunk = data[offset : offset + 1024]
            packet = self._make_packet(block_no, chunk, use_1k=True)
            if not self._send_with_ack(packet, retries):
                raise TimeoutError(f"YMODEM 数据块 {block_no} 发送失败")
            offset += len(chunk)
            block_no = (block_no % 255) + 1

        if not self._finish(retries):
            raise TimeoutError("YMODEM 结束握手失败")

        # 发送尾包（空文件名）收尾
        tail_block = self._make_packet(0, b"", use_1k=True)
        self._send_with_ack(tail_block, retries)

        return {"blocks": block_no - 1, "bytes": len(data)}

    def _wait_start(self, timeout: float) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            char = self.channel.read(1, timeout=max(0.5, deadline - time.time()))
            if not char:
                continue
            code = char[0]
            if code == CRC_REQ:
                self._log("info", "YMODEM 启动握手 OK")
                return
            if code == CAN:
                raise RuntimeError("YMODEM 被对端取消")
        raise TimeoutError("YMODEM 启动握手超时")

    def _send_with_ack(self, packet: bytes, retries: int) -> bool:
        for _ in range(retries):
            self.channel.write(packet)
            resp = self.channel.read(1, timeout=1.0)
            if resp and resp[0] == ACK:
                return True
            if resp and resp[0] == CAN:
                raise RuntimeError("YMODEM 被对端取消")
        return False

    def _finish(self, retries: int) -> bool:
        for _ in range(retries):
            self.channel.write(bytes([EOT]))
            resp = self.channel.read(1, timeout=1.0)
            if resp and resp[0] == ACK:
                return True
        return False

    @staticmethod
    def _make_packet(block_no: int, chunk: bytes, use_1k: bool) -> bytes:
        size = 1024 if use_1k else 128
        data = chunk[:size]
        if len(data) < size:
            pad_byte = b"\x00" if block_no == 0 else b"\x1A"
            data = data + pad_byte * (size - len(data))
        header = bytes([STX if use_1k else SOH, block_no & 0xFF, 0xFF - (block_no & 0xFF)])
        crc = crc16_xmodem(data).to_bytes(2, "big")
        return header + data + crc


ProtocolRegistry.register("ymodem", YModem)
