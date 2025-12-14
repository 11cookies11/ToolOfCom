from __future__ import annotations

import time
from typing import Optional

from dsl.ast_nodes import ScriptAST, State
from dsl.expression import eval_expr
from runtime.context import RuntimeContext


class StateMachineExecutor:
    """简单的状态机虚拟机：执行 do -> 事件/超时 -> 条件跳转。"""

    def __init__(self, ast: ScriptAST, context: RuntimeContext) -> None:
        self.ast = ast
        self.ctx = context
        self.current: Optional[State] = ast.state_machine.states[ast.state_machine.initial]
        self.done = False

    def run(self) -> None:
        if self.current and hasattr(self.ctx, "record_state"):
            try:
                self.ctx.record_state(self.current.name)
            except Exception:
                pass
        while not self.done and self.current:
            state = self.current
            self.ctx.logger.info(f"[STATE] {state.name}")
            self._run_actions(state)

            # 条件 goto
            if state.goto:
                if state.when:
                    cond = bool(eval_expr(state.when, self.ctx.vars_snapshot()))
                    target = state.goto if cond else state.else_goto
                    if target:
                        self._goto(target)
                        continue
                else:
                    self._goto(state.goto)
                    continue

            # 事件/超时
            next_state = self._wait_event_or_timeout(state)
            if next_state:
                self._goto(next_state)
            else:
                self.done = True

    def _run_actions(self, state: State) -> None:
        for action in state.actions:
            self.ctx.logger.debug(f"  do: {action.name} {action.args}")
            self.ctx.run_action(action.name, action.args)

    def _wait_event_or_timeout(self, state: State) -> Optional[str]:
        if not state.on_event and not state.timeout:
            return None
        deadline = time.time() + (state.timeout / 1000.0 if state.timeout else 1e9)
        while time.time() <= deadline and not self.done:
            evt = self.ctx.next_event(timeout=0.1)
            if evt is None:
                continue
            self.ctx.logger.debug(f"  event: {evt}")
            if evt in state.on_event:
                return state.on_event[evt]
        return state.on_timeout

    def _goto(self, name: str) -> None:
        if name not in self.ast.state_machine.states:
            self.ctx.logger.warning(f"未知状态: {name}")
            self.done = True
            return
        self.current = self.ast.state_machine.states[name]
        if self.current and hasattr(self.ctx, "record_state"):
            try:
                self.ctx.record_state(self.current.name)
            except Exception:
                pass
        if self.current.name == "done":
            self.done = True
