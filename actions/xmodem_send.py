from __future__ import annotations

from typing import Any, Dict

from protocols.registry import ProtocolRegistry


def run(task: Dict[str, Any], channels: Dict[str, Any], logger) -> Any:
    channel_name = task.get("channel")
    if not channel_name or channel_name not in channels:
        raise KeyError(f"未找到通道: {channel_name}")
    file_path = task.get("file") or task.get("path")
    if not file_path:
        raise ValueError("xmodem_send 需要 file/path 参数")

    retries = int(task.get("retries", 10))
    start_timeout = float(task.get("start_timeout", 10.0))

    protocol_cls = ProtocolRegistry.get("xmodem")
    protocol = protocol_cls(channels[channel_name], logger)
    return protocol.execute(file_path=file_path, retries=retries, start_timeout=start_timeout)
