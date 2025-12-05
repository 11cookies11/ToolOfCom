"""协议装载与解析：基于 YAML 配置增量解析串口字节流，发布协议事件。

约定的帧格式（可根据需求扩展/调整）：
    header | cmd(1B) | length(2B, big-endian) | payload | crc(opt) | tail(opt)
CRC 计算范围：cmd + length + payload
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from core.event_bus import EventBus


def crc16_modbus(data: bytes) -> int:
    """标准 CRC16-Modbus，多项式 0xA001，初值 0xFFFF。"""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def crc8(data: bytes, poly: int = 0x07, init: int = 0x00) -> int:
    """简单 CRC8 实现，缺省多项式 0x07。"""
    crc = init
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ poly) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc & 0xFF


class ProtocolLoader:
    def __init__(self, bus: EventBus, config_path: str = "config/protocol.yaml") -> None:
        self.bus = bus
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self._buffer = bytearray()
        self._header = b""
        self._tail: bytes | None = None
        self._crc_kind: Optional[str] = None
        self._max_length: int = 1024
        self._cmd_map: Dict[int, str] = {}
        self.load_config()
        # 订阅串口接收事件
        self.bus.subscribe("serial.rx", self.parse)

    def load_config(self) -> None:
        """加载 YAML 配置，并缓存关键字段。"""
        with self.config_path.open("r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f) or {}

        frame_cfg = self.config.get("frame", {})
        self._header = self._hex_to_bytes(frame_cfg.get("header", ""))
        tail_hex = frame_cfg.get("tail")
        self._tail = self._hex_to_bytes(tail_hex) if tail_hex else None
        self._crc_kind = frame_cfg.get("crc")
        self._max_length = int(frame_cfg.get("max_length", 1024))

        commands = self.config.get("commands", {}) or {}
        self._cmd_map = {int(v.get("cmd", 0)): k for k, v in commands.items()}

    def parse(self, data: bytes) -> None:
        """增量解析串口字节流，提取完整帧并发布事件。"""
        if not data:
            return
        self._buffer.extend(data)

        while True:
            # 查找头
            start = self._find_header(self._buffer)
            if start < 0:
                self._buffer.clear()
                return
            if start > 0:
                del self._buffer[:start]

            if len(self._buffer) < len(self._header) + 3:  # header + cmd(1) + len(2)
                return

            header_len = len(self._header)
            cmd = self._buffer[header_len]
            length = int.from_bytes(self._buffer[header_len + 1 : header_len + 3], "big")

            crc_len = 2 if self._crc_kind == "crc16_modbus" else 1 if self._crc_kind == "crc8" else 0
            tail_len = len(self._tail) if self._tail else 0

            frame_len = header_len + 1 + 2 + length + crc_len + tail_len
            if frame_len > self._max_length:
                self._log(f"[WARN] 超过最大帧长，丢弃: {frame_len}")
                del self._buffer[: header_len]  # 跳过头部，继续查找
                continue

            if len(self._buffer) < frame_len:
                return  # 等待更多数据

            frame = bytes(self._buffer[:frame_len])
            del self._buffer[:frame_len]

            if not self._validate_tail(frame, tail_len):
                self._log("[WARN] tail 校验失败，继续下一帧")
                continue

            payload_start = header_len + 1 + 2
            payload_end = payload_start + length
            payload = frame[payload_start:payload_end]

            if not self._validate_crc(frame, header_len, length, crc_len):
                self._log("[WARN] CRC 校验失败，继续下一帧")
                continue

            cmd_name = self._cmd_map.get(cmd, f"unknown_{cmd:#02x}")
            frame_dict = {
                "cmd": cmd_name,
                "raw_cmd": cmd,
                "payload": payload,
                "timestamp": time.time(),
            }
            self.bus.publish("protocol.frame", frame_dict)

    def send(self, cmd_name: str, payload: bytes = b"") -> bytes:
        """根据配置构造帧并发布发送事件。"""
        commands = self.config.get("commands", {}) or {}
        if cmd_name not in commands:
            raise KeyError(f"未知命令: {cmd_name}")
        raw_cmd = int(commands[cmd_name].get("cmd", 0))

        header = self._header
        length_bytes = len(payload).to_bytes(2, "big")
        body = bytes([raw_cmd]) + length_bytes + payload

        crc_bytes = b""
        if self._crc_kind == "crc16_modbus":
            crc_bytes = crc16_modbus(body).to_bytes(2, "little")
        elif self._crc_kind == "crc8":
            crc_bytes = bytes([crc8(body)])

        tail = self._tail or b""
        frame = header + body + crc_bytes + tail

        self.bus.publish("protocol.tx", frame)
        return frame

    def _find_header(self, buf: bytearray) -> int:
        if not self._header:
            return 0
        return buf.find(self._header)

    def _validate_tail(self, frame: bytes, tail_len: int) -> bool:
        if tail_len == 0 or not self._tail:
            return True
        return frame[-tail_len:] == self._tail

    def _validate_crc(self, frame: bytes, header_len: int, length: int, crc_len: int) -> bool:
        if crc_len == 0:
            return True
        body = frame[header_len : header_len + 1 + 2 + length]
        crc_bytes = frame[header_len + 1 + 2 + length : header_len + 1 + 2 + length + crc_len]
        if self._crc_kind == "crc16_modbus":
            expected = crc16_modbus(body).to_bytes(2, "little")
        elif self._crc_kind == "crc8":
            expected = bytes([crc8(body)])
        else:
            return True
        return expected == crc_bytes

    @staticmethod
    def _hex_to_bytes(hex_str: str) -> bytes:
        if not hex_str:
            return b""
        hex_str = hex_str.replace(" ", "").replace("0x", "")
        if len(hex_str) % 2 != 0:
            hex_str = "0" + hex_str
        return bytes.fromhex(hex_str)

    @staticmethod
    def _log(msg: str) -> None:
        print(f"[ProtocolLoader] {msg}")
