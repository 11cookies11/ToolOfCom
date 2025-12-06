from __future__ import annotations


def lrc_modbus_ascii(data_bytes: bytes) -> int:
    """Modbus ASCII 的 LRC 校验，结果为 1 字节。"""
    total = sum(data_bytes) & 0xFF
    return ((-total) + 256) & 0xFF
