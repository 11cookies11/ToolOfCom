from __future__ import annotations


def crc16_modbus(data: bytes) -> int:
    """CRC16-Modbus，多项式 0xA001，初始 0xFFFF。"""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def crc16_xmodem(data: bytes) -> int:
    """CRC16-XMODEM，多项式 0x1021，初始 0x0000。"""
    crc = 0x0000
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc & 0xFFFF
