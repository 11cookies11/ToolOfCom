from __future__ import annotations

from typing import Any, Dict, List

import yaml

from dsl.ast_nodes import (
    ActionCall,
    ChartSpec,
    ControlActionSpec,
    ControlInputSpec,
    ControlSpec,
    LayoutNode,
    ScriptAST,
    State,
    StateMachine,
    UIConfig,
)


def _parse_actions(items: List[Any]) -> List[ActionCall]:
    actions: List[ActionCall] = []
    for item in items or []:
        if not isinstance(item, dict):
            raise ValueError(f"非法动作定义: {item}")
        if "action" in item:
            actions.append(ActionCall(name=item["action"], args=item.get("args", {}) or {}))
        elif "if" in item:
            actions.append(ActionCall(name="if", args=item.get("if", {}) or {}))
        elif "set" in item:
            actions.append(ActionCall(name="set", args=item["set"]))
        elif "log" in item:
            actions.append(ActionCall(name="log", args={"message": item["log"]}))
        elif "wait" in item:
            args = item["wait"] if isinstance(item["wait"], dict) else {"ms": item["wait"]}
            actions.append(ActionCall(name="wait", args=args))
        elif "wait_for_event" in item:
            args = item["wait_for_event"] if isinstance(item["wait_for_event"], dict) else {"event": item["wait_for_event"]}
            actions.append(ActionCall(name="wait_for_event", args=args))
        else:
            raise ValueError(f"未知动作类型: {item}")
    return actions


def _parse_state(name: str, node: Dict[str, Any]) -> State:
    return State(
        name=name,
        actions=_parse_actions(node.get("do", [])),
        on_event=node.get("on_event", {}) or {},
        timeout=node.get("timeout"),
        on_timeout=node.get("on_timeout"),
        when=node.get("when"),
        goto=node.get("goto"),
        else_goto=node.get("else_goto"),
    )


def _parse_ui(ui_data: Dict[str, Any]) -> UIConfig:
    charts_cfg = ui_data.get("charts") or []
    charts = []
    for idx, item in enumerate(charts_cfg):
        if not isinstance(item, dict):
            raise ValueError(f"ui.charts[{idx}] must be a mapping")
        cid = str(item.get("id") or f"chart_{idx}")
        chart_type = str(item.get("type", "line")).lower()
        bind = item.get("bind")
        if chart_type == "scatter3d" and not bind:
            bind = item.get("bind_z") or item.get("bind_y") or item.get("bind_x") or cid
        if not bind:
            raise ValueError(f"ui.charts[{idx}] missing bind")
        group = item.get("group")
        separate = bool(item.get("separate", False))
        if group and separate:
            raise ValueError(f"ui.charts[{idx}] cannot have both group and separate")
        bind_x = item.get("bind_x")
        bind_y = item.get("bind_y")
        bind_z = item.get("bind_z")
        if chart_type == "scatter3d":
            if not (bind_x and bind_y and bind_z):
                raise ValueError(f"ui.charts[{idx}] scatter3d requires bind_x/bind_y/bind_z")
        charts.append(
            ChartSpec(
                id=cid,
                title=str(item.get("title", cid)),
                bind=str(bind),
                chart_type=chart_type,
                bind_x=str(bind_x) if bind_x else None,
                bind_y=str(bind_y) if bind_y else None,
                bind_z=str(bind_z) if bind_z else None,
                group=str(group) if group else None,
                separate=separate,
                max_points=int(item.get("max_points", 1000)),
            )
        )
    return UIConfig(charts=charts)
    # Controls are added later


def _parse_controls(ui_data: Dict[str, Any]) -> List[ControlSpec]:
    controls_cfg = ui_data.get("controls") or []
    controls: List[ControlSpec] = []
    for idx, item in enumerate(controls_cfg):
        if not isinstance(item, dict):
            raise ValueError(f"ui.controls[{idx}] must be a mapping")
        cid = str(item.get("id") or f"control_{idx}")
        title = str(item.get("title") or cid)
        separate = bool(item.get("separate", True))

        inputs_cfg = item.get("inputs") or []
        inputs: List[ControlInputSpec] = []
        for jdx, inp in enumerate(inputs_cfg):
            if not isinstance(inp, dict):
                raise ValueError(f"ui.controls[{idx}].inputs[{jdx}] must be a mapping")
            name = inp.get("name")
            if not name:
                raise ValueError(f"ui.controls[{idx}].inputs[{jdx}] missing name")
            itype = str(inp.get("type", "float")).lower()
            label = str(inp.get("label", name))
            options = inp.get("options") or []
            if itype == "select" and not isinstance(options, list):
                raise ValueError(f"ui.controls[{idx}].inputs[{jdx}].options must be list")
            inputs.append(
                ControlInputSpec(
                    name=str(name),
                    label=label,
                    itype=itype,
                    minimum=inp.get("min"),
                    maximum=inp.get("max"),
                    step=inp.get("step"),
                    default=inp.get("default"),
                    options=[str(opt) for opt in options] if options else [],
                    placeholder=inp.get("placeholder"),
                )
            )

        actions_cfg = item.get("actions") or {}
        actions: List[ControlActionSpec] = []
        for act_name, act_def in actions_cfg.items():
            if not isinstance(act_def, dict):
                raise ValueError(f"ui.controls[{idx}].actions.{act_name} must be a mapping")
            emit = act_def.get("emit")
            if not emit:
                raise ValueError(f"ui.controls[{idx}].actions.{act_name} missing emit")
            label = str(act_def.get("label", act_name))
            actions.append(ControlActionSpec(name=str(act_name), emit=str(emit), label=label))

        controls.append(
            ControlSpec(
                id=cid,
                title=title,
                separate=separate,
                inputs=inputs,
                actions=actions,
            )
        )
    return controls


def _parse_layout_node(node: Dict[str, Any]) -> LayoutNode:
    if "split" in node:
        orient_raw = node.get("split")
        orientation = str(orient_raw).lower()
        if orientation not in {"horizontal", "vertical"}:
            raise ValueError(f"layout split orientation invalid: {orient_raw}")
        children: List[LayoutNode] = []
        for key in ("left", "right", "top", "bottom", "children"):
            child_cfg = node.get(key)
            if child_cfg:
                if key == "children":
                    if not isinstance(child_cfg, list):
                        raise ValueError("layout.children must be list")
                    children.extend(_parse_layout_node(item) for item in child_cfg)
                else:
                    if not isinstance(child_cfg, dict):
                        raise ValueError(f"layout {key} must be mapping")
                    children.append(_parse_layout_node(child_cfg))
        if not children:
            raise ValueError("layout split requires children")
        return LayoutNode(type="split", orientation=orientation, children=children)

    charts = node.get("charts") or []
    controls = node.get("controls") or []
    if not charts and not controls:
        raise ValueError("layout leaf requires charts or controls")
    if charts and not isinstance(charts, list):
        raise ValueError("layout leaf charts must be list")
    if controls and not isinstance(controls, list):
        raise ValueError("layout leaf controls must be list")
    return LayoutNode(type="leaf", charts=[str(c) for c in charts], controls=[str(c) for c in controls])


def _parse_layout(ui_data: Dict[str, Any]) -> LayoutNode | None:
    layout_cfg = ui_data.get("layout")
    if not layout_cfg:
        return None
    if not isinstance(layout_cfg, dict):
        raise ValueError("ui.layout must be a mapping")
    return _parse_layout_node(layout_cfg)


def parse_script(path: str) -> ScriptAST:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    version = int(data.get("version", 1))
    vars_def = data.get("vars", {}) or {}
    channels = data.get("channels", {}) or {}
    ui_cfg_raw = data.get("ui") or {}
    ui_cfg = _parse_ui(ui_cfg_raw)
    ui_cfg.controls = _parse_controls(ui_cfg_raw)
    ui_cfg.layout = _parse_layout(ui_cfg_raw)

    sm_cfg = data.get("state_machine") or {}
    initial = sm_cfg.get("initial")
    states_cfg = sm_cfg.get("states") or {}
    states: Dict[str, State] = {}
    for state_name, state_node in states_cfg.items():
        states[state_name] = _parse_state(state_name, state_node)
    if not initial or initial not in states:
        raise ValueError("state_machine.initial 未定义或未在 states 中声明")

    sm = StateMachine(initial=initial, states=states)
    return ScriptAST(version=version, vars=vars_def, channels=channels, state_machine=sm, ui=ui_cfg)
