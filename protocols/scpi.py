from __future__ import annotations

import time
from typing import Any, Dict

from protocols.base import BaseProtocol
from protocols.registry import ProtocolRegistry


class SCPIProtocol(BaseProtocol):
    """Simple SCPI command/query helper."""

    def execute(
        self,
        cmd: str,
        expect_response: bool | None = None,
        timeout: float = 2.0,
        terminator: bytes | str = b"\n",
        strip: bool = True,
    ) -> Dict[str, Any]:
        term_bytes = terminator if isinstance(terminator, (bytes, bytearray)) else str(terminator).encode()
        payload = self._build_command(cmd, term_bytes)
        self.channel.write(payload)

        should_read = expect_response
        if should_read is None:
            should_read = "?" in cmd
        if not should_read:
            return {"ok": True, "raw": b"", "text": None}

        resp = self._read_response(term_bytes, timeout)
        if resp is None:
            raise TimeoutError("SCPI response timeout")

        parsed: Dict[str, Any] = {"ok": True, "raw": resp}
        if strip:
            resp = resp.rstrip(b"\r\n")

        if resp.startswith(b"#") and len(resp) >= 2 and chr(resp[1:2][0]).isdigit():
            parsed["block"] = resp
            parsed["length"] = len(resp)
        else:
            try:
                parsed["text"] = resp.decode(errors="ignore")
            except Exception:
                parsed["text"] = None
        return parsed

    def _build_command(self, cmd: str, terminator: bytes) -> bytes:
        cmd_bytes = cmd.encode() if not isinstance(cmd, (bytes, bytearray)) else bytes(cmd)
        if not cmd_bytes.endswith(terminator):
            cmd_bytes += terminator
        return cmd_bytes

    def _read_response(self, terminator: bytes, timeout: float) -> bytes | None:
        deadline = time.time() + timeout
        first = self._read_exact(1, deadline)
        if not first:
            return None

        if first == b"#":
            length_info = self._read_exact(1, deadline)
            if not length_info or not length_info.isdigit():
                return first + (length_info or b"")
            digits = int(length_info.decode())
            len_bytes = self._read_exact(digits, deadline) if digits > 0 else b""
            try:
                data_len = int(len_bytes.decode()) if len_bytes else 0
            except ValueError:
                data_len = 0
            data = self._read_exact(data_len, deadline) if data_len > 0 else b""
            tail = self._read_until_terminator(terminator, deadline)
            return b"".join([first, length_info, len_bytes, data, tail])

        rest = self._read_until_terminator(terminator, deadline)
        return first + (rest or b"")

    def _read_until_terminator(self, terminator: bytes, deadline: float) -> bytes:
        buf = bytearray()
        while time.time() < deadline:
            chunk = self.channel.read_until(terminator, timeout=max(0.01, deadline - time.time()))
            if chunk:
                buf.extend(chunk)
                if buf.endswith(terminator):
                    break
            else:
                time.sleep(0.01)
        return bytes(buf)

    def _read_exact(self, size: int, deadline: float) -> bytes | None:
        buf = bytearray()
        while len(buf) < size and time.time() < deadline:
            chunk = b""
            if hasattr(self.channel, "read_exact"):
                chunk = self.channel.read_exact(size - len(buf), timeout=max(0.01, deadline - time.time()))  # type: ignore[attr-defined]
            else:
                chunk = self.channel.read(size - len(buf), timeout=max(0.01, deadline - time.time()))
            if chunk:
                buf.extend(chunk)
            else:
                time.sleep(0.01)
        return bytes(buf) if len(buf) == size else None


ProtocolRegistry.register("scpi", SCPIProtocol)
