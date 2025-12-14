from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

from actions.registry import ActionRegistry
from dsl.expression import eval_expr


def _vars_snapshot(ctx) -> Dict[str, Any]:
    if hasattr(ctx, "vars_snapshot"):
        return ctx.vars_snapshot()
    if hasattr(ctx, "vars"):
        return dict(ctx.vars)
    return {}


def _parse_inline_actions(items: Any) -> List[Tuple[str, Dict[str, Any]]]:
    if items is None:
        return []
    if not isinstance(items, list):
        raise ValueError("inline actions must be a list")
    parsed: List[Tuple[str, Dict[str, Any]]] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError(f"invalid inline action: {item}")
        if "action" in item:
            name = item["action"]
            args = item.get("args", {}) or {}
            if not isinstance(args, dict):
                raise ValueError(f"action.args must be a mapping: {item}")
            parsed.append((str(name), args))
            continue
        if "set" in item:
            args = item.get("set") or {}
            if not isinstance(args, dict):
                raise ValueError(f"set must be a mapping: {item}")
            parsed.append(("set", args))
            continue
        if "log" in item:
            parsed.append(("log", {"message": item.get("log")}))
            continue
        if "wait" in item:
            wait_cfg = item.get("wait")
            args = wait_cfg if isinstance(wait_cfg, dict) else {"ms": wait_cfg}
            parsed.append(("wait", args))
            continue
        if "wait_for_event" in item:
            wfe = item.get("wait_for_event")
            args = wfe if isinstance(wfe, dict) else {"event": wfe}
            parsed.append(("wait_for_event", args))
            continue
        if "if" in item:
            if_cfg = item.get("if") or {}
            if not isinstance(if_cfg, dict):
                raise ValueError(f"if must be a mapping: {item}")
            parsed.append(("if", if_cfg))
            continue
        raise ValueError(f"unknown inline action type: {item}")
    return parsed


def action_if(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    cond_expr = args.get("when") or args.get("cond")
    if not cond_expr:
        raise ValueError("if requires 'when'")
    cond = bool(eval_expr(str(cond_expr), _vars_snapshot(ctx)))
    then_items = args.get("then") or args.get("do") or []
    else_items = args.get("else") or args.get("otherwise") or []
    items = then_items if cond else else_items
    actions = _parse_inline_actions(items)
    for name, a in actions:
        ctx.run_action(name, a)
    return {"when": str(cond_expr), "taken": "then" if cond else "else", "count": len(actions)}


def _iterable_or_error(value: Any, *, name: str) -> Iterable[Any]:
    if isinstance(value, (list, tuple)):
        return value
    raise ValueError(f"{name} must be a list/tuple")


def _item_env(item: Any, index: int) -> Dict[str, Any]:
    env: Dict[str, Any] = {"item": item, "index": index}
    if isinstance(item, dict):
        for k, v in item.items():
            if isinstance(k, str) and k.isidentifier():
                env[f"item.{k}"] = v
    return env


def action_list_filter(ctx, args: Dict[str, Any]) -> List[Any]:
    src = args.get("src") or args.get("items") or args.get("in")
    if src is None:
        raise ValueError("list_filter requires 'src'")
    src_val = ctx.eval_value(src) if hasattr(ctx, "eval_value") else src
    if isinstance(src, str) and "$" not in src and hasattr(ctx, "vars") and src in ctx.vars:
        src_val = ctx.vars[src]
    where = args.get("where") or args.get("when")
    if not where:
        raise ValueError("list_filter requires 'where'")
    limit = args.get("limit")
    out: List[Any] = []
    base = _vars_snapshot(ctx)
    for idx, item in enumerate(_iterable_or_error(src_val, name="src")):
        env = dict(base)
        env.update(_item_env(item, idx))
        if bool(eval_expr(str(where), env)):
            out.append(item)
            if limit is not None and len(out) >= int(limit):
                break
    dst = args.get("dst") or args.get("out")
    if dst and hasattr(ctx, "set_var"):
        ctx.set_var(str(dst), out)
    return out


def action_list_map(ctx, args: Dict[str, Any]) -> List[Any]:
    src = args.get("src") or args.get("items") or args.get("in")
    if src is None:
        raise ValueError("list_map requires 'src'")
    src_val = ctx.eval_value(src) if hasattr(ctx, "eval_value") else src
    if isinstance(src, str) and "$" not in src and hasattr(ctx, "vars") and src in ctx.vars:
        src_val = ctx.vars[src]
    expr = args.get("expr") or args.get("map") or args.get("value")
    if expr is None:
        raise ValueError("list_map requires 'expr'")
    where = args.get("where") or args.get("when")
    limit = args.get("limit")
    out: List[Any] = []
    base = _vars_snapshot(ctx)
    for idx, item in enumerate(_iterable_or_error(src_val, name="src")):
        env = dict(base)
        env.update(_item_env(item, idx))
        if where and not bool(eval_expr(str(where), env)):
            continue
        out.append(eval_expr(str(expr), env))
        if limit is not None and len(out) >= int(limit):
            break
    dst = args.get("dst") or args.get("out")
    if dst and hasattr(ctx, "set_var"):
        ctx.set_var(str(dst), out)
    return out


def register_data_actions() -> None:
    ActionRegistry.register("if", action_if)
    ActionRegistry.register("list_filter", action_list_filter)
    ActionRegistry.register("list_map", action_list_map)

