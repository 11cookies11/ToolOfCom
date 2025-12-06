from __future__ import annotations

import time
from typing import Optional

from protocols.modbus_base import ModbusBase
from protocols.registry import ProtocolRegistry
from utils.crc16 import crc16_modbus


class ModbusRTU(ModbusBase):
    """Modbus RTU：带 CRC16 的二进制帧。"""

    def execute(
        self,
        function: int,
        address: int,
        quantity: int = 1,
        values=None,
        unit_id: int = 1,
        retries: int = 3,
        timeout: int = 1000,
    ):
        request_pdu = self.build_request(function, address, quantity, values, unit_id)
        frame = bytes([unit_id & 0xFF]) + request_pdu
        frame += crc16_modbus(frame).to_bytes(2, "little")

        last_error: Optional[Exception] = None
        for attempt in range(1, retries + 1):
            self._log("info", f"RTU TX 尝试 {attempt}/{retries}")
            self.channel.write(frame)
            resp = self._read_frame(timeout / 1000.0)
            if not resp:
                last_error = TimeoutError("Modbus RTU 超时未响应")
                continue

            if len(resp) < 5:
                last_error = ValueError("Modbus RTU 响应长度不足")
                continue

            if not self._check_crc(resp):
                last_error = ValueError("Modbus RTU CRC 校验失败")
                continue

            if resp[0] != (unit_id & 0xFF):
                last_error = ValueError(f"Modbus RTU 单元号不匹配: {resp[0]}")
                continue

            return self.parse_response(resp[1:-2])

        if last_error:
            raise last_error
        raise TimeoutError("Modbus RTU 重试耗尽")

    def _check_crc(self, frame: bytes) -> bool:
        if len(frame) < 3:
            return False
        calc = crc16_modbus(frame[:-2]).to_bytes(2, "little")
        return calc == frame[-2:]

    def _read_frame(self, timeout_s: float) -> Optional[bytes]:
        deadline = time.time() + timeout_s
        buf = bytearray()
        while time.time() < deadline:
            chunk = self.channel.read(256, timeout=max(0.01, deadline - time.time()))
            if chunk:
                buf.extend(chunk)
                expected_len = self._guess_length(buf)
                if expected_len and len(buf) >= expected_len:
                    return bytes(buf[:expected_len])
            else:
                time.sleep(0.01)
        return bytes(buf) if buf else None

    @staticmethod
    def _guess_length(buf: bytearray) -> Optional[int]:
        if len(buf) < 3:
            return None
        func = buf[1]
        if func in {0x01, 0x02, 0x03, 0x04} and len(buf) >= 3:
            byte_count = buf[2]
            return 3 + byte_count + 2
        if func in {0x05, 0x06, 0x0F, 0x10}:
            return 8  # 固定长度：addr(1)+func(1)+address(2)+qty/value(2)+CRC(2)
        if func == 0x11 and len(buf) >= 3:
            byte_count = buf[2]
            return 3 + byte_count + 2
        if func & 0x80:
            return 5  # 异常响应：addr+func+code+CRC
        return None


ProtocolRegistry.register("modbus_rtu", ModbusRTU)
