from __future__ import annotations

import itertools
import time

from protocols.modbus_base import ModbusBase
from protocols.registry import ProtocolRegistry


class ModbusTCP(ModbusBase):
    """Modbus TCP：MBAP 头 + PDU，无需 CRC。"""

    def __init__(self, channel, logger=None) -> None:
        super().__init__(channel, logger)
        self._tid = itertools.count(1)

    def execute(
        self,
        function: int,
        address: int,
        quantity: int = 1,
        values=None,
        unit_id: int = 1,
        timeout: float = 2.0,
    ):
        pdu = self.build_request(function, address, quantity, values, unit_id)
        tid = next(self._tid) & 0xFFFF
        length = len(pdu) + 1  # UnitID + PDU
        header = tid.to_bytes(2, "big") + b"\x00\x00" + length.to_bytes(2, "big") + bytes([unit_id & 0xFF])
        frame = header + pdu

        self.channel.write(frame)

        header_resp = self._read_exact(7, timeout)
        if not header_resp or len(header_resp) != 7:
            raise TimeoutError("Modbus TCP 响应头超时")

        resp_tid = int.from_bytes(header_resp[0:2], "big")
        proto_id = int.from_bytes(header_resp[2:4], "big")
        length_resp = int.from_bytes(header_resp[4:6], "big")
        resp_uid = header_resp[6]

        if resp_tid != tid:
            raise ValueError(f"Modbus TCP 事务号不匹配: {resp_tid} != {tid}")
        if proto_id != 0:
            raise ValueError(f"Modbus TCP protocol_id 异常: {proto_id}")
        if resp_uid != (unit_id & 0xFF):
            raise ValueError(f"Modbus TCP 单元号不匹配: {resp_uid}")

        pdu_len = max(0, length_resp - 1)
        pdu_resp = self._read_exact(pdu_len, timeout)
        if pdu_resp is None or len(pdu_resp) != pdu_len:
            raise TimeoutError("Modbus TCP 读取 PDU 超时")

        return self.parse_response(pdu_resp)

    def _read_exact(self, size: int, timeout: float) -> bytes | None:
        buf = bytearray()
        deadline = time.time() + timeout
        while len(buf) < size and time.time() < deadline:
            chunk = self.channel.read(size - len(buf), timeout=max(0.01, deadline - time.time()))
            if chunk:
                buf.extend(chunk)
            else:
                time.sleep(0.01)
        return bytes(buf) if len(buf) == size else None


ProtocolRegistry.register("modbus_tcp", ModbusTCP)
