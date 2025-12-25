from __future__ import annotations

import time
from typing import List

from protocols.base import BaseProtocol
from protocols.registry import ProtocolRegistry


class ATProtocol(BaseProtocol):
    """AT 指令处理器，基于字节流通道。"""

    def execute(
        self,
        cmd: str,
        timeout: float = 2.0,
        terminator: bytes | str = b"\r\n",
        ok: str = "OK",
        error: str = "ERROR",
        echo: bool = True,
    ):
        terminator_bytes = terminator if isinstance(terminator, (bytes, bytearray)) else str(terminator).encode()
        payload = self._build_command(cmd, terminator_bytes)
        self.channel.write(payload)

        deadline = time.time() + timeout
        lines: List[str] = []

        while time.time() < deadline:
            line = self._read_line(deadline, terminator_bytes)
            if line is None:
                continue

            text = line.decode(errors="ignore").strip()
            if not text:
                continue

            if echo and text.upper() == cmd.strip().upper():
                continue

            if text.upper() == ok.upper():
                return {"ok": True, "lines": lines}

            if text.upper().startswith(error.upper()):
                return {"ok": False, "lines": lines, "error": text}

            lines.append(text)

        raise TimeoutError("AT command timeout waiting for OK/ERROR")

    def _build_command(self, cmd: str, terminator: bytes) -> bytes:
        cmd_txt = cmd.strip()
        if not cmd_txt.upper().startswith("AT"):
            cmd_txt = "AT" + cmd_txt
        cmd_bytes = cmd_txt.encode()
        if not cmd_bytes.endswith(terminator):
            cmd_bytes += terminator
        return cmd_bytes

    def _read_line(self, deadline: float, terminator: bytes) -> bytes | None:
        remaining = deadline - time.time()
        if remaining <= 0:
            return None
        data = self.channel.read_until(terminator, timeout=remaining)
        return data if data else None


ProtocolRegistry.register("at", ATProtocol)
