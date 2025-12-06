from __future__ import annotations

import time

from protocols.modbus_base import ModbusBase
from protocols.registry import ProtocolRegistry
from utils.lrc import lrc_modbus_ascii


class ModbusASCII(ModbusBase):
    """Modbus ASCII：文本帧，LRC 校验。"""

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
        payload = bytes([unit_id & 0xFF]) + request_pdu
        lrc = lrc_modbus_ascii(payload)
        frame = f":{payload.hex().upper()}{lrc:02X}\r\n".encode("ascii")

        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            self._log("info", f"ASCII TX 尝试 {attempt}/{retries}")
            self.channel.write(frame)
            raw_line = self._read_line(timeout / 1000.0)
            if not raw_line:
                last_error = TimeoutError("Modbus ASCII 超时未响应")
                continue

            decoded = self._decode_frame(raw_line)
            if not decoded:
                last_error = ValueError("Modbus ASCII 解码失败")
                continue

            if not self._check_lrc(decoded):
                last_error = ValueError("Modbus ASCII LRC 校验失败")
                continue

            data = decoded[:-1]  # 去掉 LRC
            if data[0] != (unit_id & 0xFF):
                last_error = ValueError(f"Modbus ASCII 单元号不匹配: {data[0]}")
                continue

            return self.parse_response(data[1:])

        if last_error:
            raise last_error
        raise TimeoutError("Modbus ASCII 重试耗尽")

    def _read_line(self, timeout_s: float):
        return self.channel.read_until(b"\r\n", timeout=timeout_s)

    @staticmethod
    def _decode_frame(line: bytes) -> bytes | None:
        text = line.decode(errors="ignore").strip()
        if not text:
            return None
        if text[0] == ":":
            text = text[1:]
        if len(text) < 4 or len(text) % 2 != 0:
            return None
        try:
            return bytes.fromhex(text)
        except ValueError:
            return None

    @staticmethod
    def _check_lrc(payload_with_lrc: bytes) -> bool:
        if len(payload_with_lrc) < 2:
            return False
        data, lrc = payload_with_lrc[:-1], payload_with_lrc[-1]
        return lrc_modbus_ascii(data) == lrc


ProtocolRegistry.register("modbus_ascii", ModbusASCII)
