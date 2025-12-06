from __future__ import annotations

import time
from pathlib import Path

from protocols.base import BaseProtocol
from protocols.registry import ProtocolRegistry
from utils.crc16 import crc16_xmodem


SOH = 0x01
EOT = 0x04
ACK = 0x06
NAK = 0x15
CAN = 0x18
CRC_REQ = 0x43  # 'C'


class XModem(BaseProtocol):
    """XMODEM 固件发送（128 字节帧，CRC/XOR 校验）。"""

    def execute(self, file_path: str, retries: int = 10, start_timeout: float = 10.0):
        data = Path(file_path).read_bytes()
        crc_mode = self._wait_start(start_timeout)
        block_no = 1
        offset = 0

        while offset < len(data):
            chunk = data[offset : offset + 128]
            packet = self._make_packet(block_no, chunk, crc_mode)
            if not self._send_with_ack(packet, retries):
                raise TimeoutError(f"XMODEM 数据块 {block_no} 重试耗尽")
            offset += len(chunk)
            block_no = (block_no % 255) + 1

        if not self._finish(retries):
            raise TimeoutError("XMODEM 结束握手失败")

        return {"blocks": block_no - 1, "bytes": len(data)}

    def _wait_start(self, timeout: float) -> bool:
        """等待接收端发出 'C' 或 NAK，返回是否使用 CRC 模式。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            char = self.channel.read(1, timeout=max(0.5, deadline - time.time()))
            if not char:
                continue
            code = char[0]
            if code in {CRC_REQ, NAK}:
                self._log("info", f"XMODEM 启动握手: {chr(code)}")
                return code == CRC_REQ
            if code == CAN:
                raise RuntimeError("XMODEM 被对端取消")
        raise TimeoutError("XMODEM 启动握手超时")

    def _send_with_ack(self, packet: bytes, retries: int) -> bool:
        for _ in range(retries):
            self.channel.write(packet)
            resp = self.channel.read(1, timeout=1.0)
            if resp and resp[0] == ACK:
                return True
            if resp and resp[0] == CAN:
                raise RuntimeError("XMODEM 被对端取消")
        return False

    def _finish(self, retries: int) -> bool:
        for _ in range(retries):
            self.channel.write(bytes([EOT]))
            resp = self.channel.read(1, timeout=1.0)
            if resp and resp[0] == ACK:
                return True
        return False

    @staticmethod
    def _make_packet(block_no: int, chunk: bytes, crc_mode: bool) -> bytes:
        data = chunk + b"\x1A" * (128 - len(chunk)) if len(chunk) < 128 else chunk[:128]
        header = bytes([SOH, block_no & 0xFF, 0xFF - (block_no & 0xFF)])
        if crc_mode:
            crc = crc16_xmodem(data).to_bytes(2, "big")
            return header + data + crc
        checksum = sum(data) & 0xFF
        return header + data + bytes([checksum])


ProtocolRegistry.register("xmodem", XModem)
