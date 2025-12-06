from __future__ import annotations

from typing import Iterable, List, Sequence

from protocols.base import BaseProtocol


class ModbusBase(BaseProtocol):
    """Modbus 公共逻辑：构造 PDU、解析响应。"""

    def build_request(
        self,
        function: int,
        address: int,
        quantity: int = 1,
        values: Sequence[int] | bytes | None = None,
        unit_id: int = 1,
    ) -> bytes:
        pdu = bytearray()
        pdu.append(function & 0xFF)
        pdu.extend(self.pack_u16(address))

        if function in {0x01, 0x02, 0x03, 0x04, 0x0F, 0x10}:
            pdu.extend(self.pack_u16(quantity))

        if function in {0x05, 0x06}:
            val = self._first(values)
            if function == 0x05:
                pdu.extend(b"\xFF\x00" if val else b"\x00\x00")
            else:
                pdu.extend(self.pack_u16(val))
        elif function == 0x0F:
            bits = self._normalize_bits(values, quantity)
            byte_count = (quantity + 7) // 8
            pdu.append(byte_count)
            pdu.extend(bits[:byte_count])
        elif function == 0x10:
            regs = self._normalize_registers(values, quantity)
            pdu.append(len(regs) * 2)
            for reg in regs:
                pdu.extend(self.pack_u16(reg))
        elif function == 0x11:
            # Report Slave ID 无附加字段
            pass

        return bytes(pdu)

    def parse_response(self, response: bytes):
        if len(response) < 2:
            raise ValueError("响应长度不足")
        function = response[0]
        if function & 0x80:
            code = response[1] if len(response) > 1 else None
            return {"function": function & 0x7F, "exception": code}

        if function in {0x01, 0x02}:
            byte_count = response[1]
            data_bytes = response[2 : 2 + byte_count]
            bits: List[bool] = []
            for idx in range(byte_count * 8):
                byte_index = idx // 8
                bit_index = idx % 8
                if byte_index >= len(data_bytes):
                    break
                bits.append(bool(data_bytes[byte_index] & (1 << bit_index)))
            return {"function": function, "bits": bits}

        if function in {0x03, 0x04}:
            byte_count = response[1]
            data_bytes = response[2 : 2 + byte_count]
            registers = [
                self.unpack_u16(data_bytes[i], data_bytes[i + 1])
                for i in range(0, len(data_bytes), 2)
                if i + 1 < len(data_bytes)
            ]
            return {"function": function, "registers": registers}

        if function in {0x05, 0x06} and len(response) >= 5:
            addr = self.unpack_u16(response[1], response[2])
            val = self.unpack_u16(response[3], response[4])
            return {"function": function, "address": addr, "value": val}

        if function in {0x0F, 0x10} and len(response) >= 5:
            addr = self.unpack_u16(response[1], response[2])
            qty = self.unpack_u16(response[3], response[4])
            return {"function": function, "address": addr, "quantity": qty}

        if function == 0x11:
            byte_count = response[1] if len(response) > 1 else 0
            data_bytes = response[2 : 2 + byte_count]
            return {"function": function, "data": data_bytes}

        return {"function": function, "raw": response[1:]}

    @staticmethod
    def pack_u16(value: int) -> bytes:
        return bytes([(value >> 8) & 0xFF, value & 0xFF])

    @staticmethod
    def unpack_u16(high: int, low: int) -> int:
        return ((high & 0xFF) << 8) | (low & 0xFF)

    @staticmethod
    def _first(values: Sequence[int] | bytes | None) -> int:
        if values is None:
            return 0
        if isinstance(values, (bytes, bytearray)) and values:
            return values[0]
        try:
            return int(list(values)[0])
        except Exception:
            return 0

    @staticmethod
    def _normalize_bits(values: Sequence[int] | bytes | None, quantity: int) -> bytes:
        bits = [0] * quantity
        if values is not None:
            for idx, val in enumerate(values):
                if idx >= quantity:
                    break
                bits[idx] = 1 if bool(val) else 0
        packed = bytearray()
        for i in range(0, quantity, 8):
            byte_val = 0
            for bit in range(8):
                if i + bit >= quantity:
                    break
                if bits[i + bit]:
                    byte_val |= 1 << bit
            packed.append(byte_val)
        return bytes(packed)

    @staticmethod
    def _normalize_registers(values: Iterable[int] | None, quantity: int) -> List[int]:
        regs: List[int] = []
        if values is not None:
            for val in values:
                if len(regs) >= quantity:
                    break
                regs.append(int(val) & 0xFFFF)
        while len(regs) < quantity:
            regs.append(0)
        return regs
