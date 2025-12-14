from __future__ import annotations

import logging
import os
import tempfile
import threading
import time

from PySide6.QtCore import QThread, Signal

from actions.builtin_actions import register_builtin_actions
from actions.protocol_actions import register_protocol_actions
from actions.schema_protocol import register_schema_protocol_actions
from actions.chart_actions import register_chart_actions
from actions.record_actions import register_record_actions
from actions.data_actions import register_data_actions
from dsl.executor import StateMachineExecutor
from dsl.parser import parse_script
from runtime.channels import build_channels
from runtime.context import RuntimeContext


class _LogHandler(logging.Handler):
    """将 logging 输出转发到 Qt 信号。"""

    def __init__(self, emit_fn) -> None:
        super().__init__()
        self._emit_fn = emit_fn

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - Qt 回调
        msg = self.format(record)
        try:
            self._emit_fn(msg)
        except Exception:
            pass


class _ObservableExecutor(StateMachineExecutor):
    """带停止标记与进度回调的执行器包装。"""

    def __init__(self, ast, ctx, stop_event: threading.Event, on_state, on_progress) -> None:
        super().__init__(ast, ctx)
        self._stop_event = stop_event
        self._on_state = on_state
        self._on_progress = on_progress
        self._visited = 0
        self._total = max(1, len(ast.state_machine.states))

    def run(self) -> None:
        if self.current:
            self._notify(self.current.name)
        while not self.done and not self._stop_event.is_set() and self.current:
            state = self.current
            self._run_actions(state)
            if self._stop_event.is_set():
                break
            # 条件跳转
            if state.goto:
                if state.when:
                    cond = bool(self.ctx.eval_value(state.when))
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

    def _wait_event_or_timeout(self, state):
        if not state.on_event and not state.timeout:
            return None
        deadline = time.time() + (state.timeout / 1000.0 if state.timeout else 1e9)
        while time.time() <= deadline and not self.done and not self._stop_event.is_set():
            evt = self.ctx.next_event(timeout=0.1)
            if evt is None:
                continue
            self.ctx.logger.debug(f"  event: {evt}")
            if evt in state.on_event:
                return state.on_event[evt]
        return state.on_timeout

    def _goto(self, name: str) -> None:
        super()._goto(name)
        if self.current:
            self._notify(self.current.name)

    def _notify(self, name: str) -> None:
        self._visited += 1
        progress = int(min(1.0, self._visited / self._total) * 100)
        self._on_state(name)
        self._on_progress(progress)


class ScriptRunnerQt(QThread):
    """在后台线程运行 DSL，并通过信号回传 log/state/progress。"""

    sig_log = Signal(str)
    sig_state = Signal(str)
    sig_progress = Signal(int)

    def __init__(self, yaml_text: str, bus=None, external_events: list[str] | None = None) -> None:
        super().__init__()
        self.yaml_text = yaml_text
        self.bus = bus
        self.external_events = external_events or []
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:  # pragma: no cover - 线程逻辑
        handler = _LogHandler(lambda msg: self.sig_log.emit(msg))
        handler.setLevel(logging.INFO)
        logger = logging.getLogger("dsl")
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)

        # 注册动作
        register_builtin_actions()
        register_protocol_actions()
        register_schema_protocol_actions()
        register_chart_actions()
        register_record_actions()
        register_data_actions()

        channels = {}
        ctx = None
        tmp_path: str | None = None
        try:
            # 将编辑器内容写入临时文件，复用 parser
            with tempfile.NamedTemporaryFile("w+", suffix=".yaml", delete=False) as tmp:
                tmp.write(self.yaml_text)
                tmp.flush()
                tmp_path = tmp.name
            ast = parse_script(tmp_path)
            channels = build_channels(ast.channels)
            if not channels:
                raise ValueError("未定义 channels")
            default_channel = next(iter(channels.keys()))
            ctx = RuntimeContext(
                channels,
                default_channel,
                vars_init=ast.vars,
                bus=self.bus,
                external_events=self.external_events,
                script_text=self.yaml_text,
            )

            executor = _ObservableExecutor(
                ast,
                ctx,
                stop_event=self._stop_event,
                on_state=lambda s: self.sig_state.emit(s),
                on_progress=lambda p: self.sig_progress.emit(p),
            )
            executor.run()
            if self._stop_event.is_set():
                self.sig_log.emit("Script stopped")
            else:
                self.sig_log.emit("Script finished")
        except Exception as exc:  # 报错直接显示
            self.sig_log.emit(f"[ERROR] {exc}")
        finally:
            if ctx is not None:
                try:
                    ctx.close()
                except Exception:
                    pass
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
            for ch in channels.values():
                if hasattr(ch, "close"):
                    try:
                        ch.close()  # type: ignore[attr-defined]
                    except Exception:
                        pass
