from __future__ import annotations

from typing import Any, Dict

from actions.registry import ActionRegistry
from runtime.experiment_recorder import ExperimentRecorder


def _eval_str(ctx, value: Any) -> str:
    v = ctx.eval_value(value) if hasattr(ctx, "eval_value") else value
    return str(v) if v is not None else ""


def action_record_start(ctx, args: Dict[str, Any]):
    if getattr(ctx, "recorder", None) is not None:
        # Already recording; return current path if available.
        rec = ctx.recorder
        return str(getattr(rec, "paths", {}).root) if rec else None

    base_dir = _eval_str(ctx, args.get("dir", "logs/experiments")) or "logs/experiments"
    name = _eval_str(ctx, args.get("name", "run")) or "run"
    script_text = args.get("script_text")
    script_path = args.get("script_path")

    if script_text is not None and hasattr(ctx, "eval_value"):
        script_text = ctx.eval_value(script_text)
    script_text = str(script_text) if script_text else getattr(ctx, "script_text", None)

    if script_path is not None and hasattr(ctx, "eval_value"):
        script_path = ctx.eval_value(script_path)
    script_path = str(script_path) if script_path else getattr(ctx, "script_path", None)

    rec = ExperimentRecorder(base_dir=base_dir, name=name, script_text=script_text, script_path=script_path)
    root = rec.start()

    if hasattr(ctx, "attach_recorder"):
        ctx.attach_recorder(rec)
    else:
        ctx.recorder = rec
    if hasattr(ctx, "logger"):
        try:
            ctx.logger.info(f"[REC] start -> {root}")
        except Exception:
            pass
    if hasattr(ctx, "set_var"):
        try:
            ctx.set_var("record_dir", str(root))
        except Exception:
            pass
    return str(root)


def action_record_stop(ctx, args: Dict[str, Any]):
    rec = getattr(ctx, "recorder", None)
    if rec is None:
        return None
    vars_snapshot = None
    if hasattr(ctx, "vars_snapshot"):
        try:
            vars_snapshot = ctx.vars_snapshot()
        except Exception:
            vars_snapshot = None
    try:
        rec.close(vars_snapshot=vars_snapshot)
    finally:
        if hasattr(ctx, "detach_recorder"):
            ctx.detach_recorder()
        else:
            ctx.recorder = None
    if hasattr(ctx, "logger"):
        try:
            ctx.logger.info(f"[REC] stop -> {rec.paths.root}")
        except Exception:
            pass
    return str(rec.paths.root)


def register_record_actions() -> None:
    ActionRegistry.register("record_start", action_record_start)
    ActionRegistry.register("record_stop", action_record_stop)
