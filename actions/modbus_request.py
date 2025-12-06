from __future__ import annotations

from typing import Any, Dict

from protocols.registry import ProtocolRegistry

_MAP = {
    "rtu": "modbus_rtu",
    "ascii": "modbus_ascii",
    "tcp": "modbus_tcp",
}


def run(task: Dict[str, Any], channels: Dict[str, Any], logger) -> Any:
    protocol_key = _MAP.get(str(task.get("protocol", "")).lower())
    if not protocol_key:
        raise ValueError("modbus_request.protocol 必须为 rtu / ascii / tcp")

    channel_name = task.get("channel")
    if not channel_name or channel_name not in channels:
        raise KeyError(f"未找到通道: {channel_name}")

    function = int(task.get("function"))
    address = int(task.get("address"))
    quantity = int(task.get("quantity", 1))
    values = task.get("values")
    unit_id = int(task.get("unit_id", 1))

    protocol_cls = ProtocolRegistry.get(protocol_key)
    protocol = protocol_cls(channels[channel_name], logger)

    if protocol_key == "modbus_tcp":
        timeout_s = float(task.get("timeout", 2.0))
        return protocol.execute(function=function, address=address, quantity=quantity, values=values, unit_id=unit_id, timeout=timeout_s)

    retries = int(task.get("retries", 3))
    timeout_ms = int(task.get("timeout", 1000))
    return protocol.execute(
        function=function,
        address=address,
        quantity=quantity,
        values=values,
        unit_id=unit_id,
        retries=retries,
        timeout=timeout_ms,
    )
