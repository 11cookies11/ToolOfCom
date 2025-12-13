from __future__ import annotations

import time
from typing import Any, Dict

from actions.chart_bridge import chart_bridge
from actions.registry import ActionRegistry


def _eval(ctx, val: Any) -> Any:
    if hasattr(ctx, "eval_value"):
        return ctx.eval_value(val)
    return val


def action_chart_add(ctx, args: Dict[str, Any]):
    """Push a data point to chart system. Args: bind (str), value (num or expr), ts (seconds, optional)."""
    if chart_bridge is None:
        ctx.logger.warning("chart bridge unavailable (Qt not loaded)")
        return None
    bind = args.get("bind")
    if not bind:
        raise ValueError("chart_add requires bind")
    raw_val = args.get("value", args.get("val"))
    if raw_val is None:
        raise ValueError("chart_add requires value")
    ts_arg = args.get("ts") or args.get("timestamp")
    ts = float(_eval(ctx, ts_arg)) if ts_arg is not None else time.time()
    try:
        val = float(_eval(ctx, raw_val))
    except Exception as exc:
        raise ValueError(f"chart_add value invalid: {exc}") from exc
    chart_bridge.sig_data.emit({"ts": ts, str(bind): val})
    return {"ts": ts, "bind": str(bind), "value": val}


def action_chart_add3d(ctx, args: Dict[str, Any]):
    """Push a 3D point. Args: x,y,z (expr), ts(optional), bind_x/y/z(optional keys, default x/y/z)."""
    if chart_bridge is None:
        ctx.logger.warning("chart bridge unavailable (Qt not loaded)")
        return None
    bx = str(args.get("bind_x", "x"))
    by = str(args.get("bind_y", "y"))
    bz = str(args.get("bind_z", "z"))
    if args.get("x") is None or args.get("y") is None or args.get("z") is None:
        raise ValueError("chart_add3d requires x, y, z")
    x_val = _eval(ctx, args.get("x"))
    y_val = _eval(ctx, args.get("y"))
    z_val = _eval(ctx, args.get("z"))
    ts_arg = args.get("ts") or args.get("timestamp")
    ts = float(_eval(ctx, ts_arg)) if ts_arg is not None else time.time()
    payload = {"ts": ts, bx: x_val, by: y_val, bz: z_val}
    chart_bridge.sig_data.emit(payload)
    return payload


def register_chart_actions() -> None:
    ActionRegistry.register("chart_add", action_chart_add)
    ActionRegistry.register("chart_add3d", action_chart_add3d)
