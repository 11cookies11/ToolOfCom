from __future__ import annotations

import logging
import queue
from typing import Any, Dict, Optional

from actions.registry import ActionRegistry
from dsl.expression import eval_expr
from runtime.experiment_recorder import ExperimentRecorder, JsonlLogHandler


class RuntimeContext:
    def __init__(
        self,
        channels: Dict[str, Any],
        default_channel: str,
        vars_init: Dict[str, Any],
        bus=None,
        external_events: Optional[list[str]] = None,
        script_path: Optional[str] = None,
        script_text: Optional[str] = None,
    ) -> None:
        self.channels = channels
        self.channel = channels[default_channel]
        self.vars: Dict[str, Any] = dict(vars_init)
        self.logger = logging.getLogger("dsl")
        self.script_path = script_path
        self.script_text = script_text
        self._last_event: Any = None
        self._last_event_name: Optional[str] = None
        self._last_event_payload: Any = None
        self._bus = bus
        self._bus_handlers: list[tuple[str, Any]] = []
        self._event_queue: "queue.SimpleQueue[tuple[str, Any]]" = queue.SimpleQueue()
        self._recorder: Optional[ExperimentRecorder] = None
        self._recorder_log_handler: Optional[JsonlLogHandler] = None
        if self._bus and external_events:
            for name in external_events:
                handler = self._make_bus_handler(name)
                self._bus.subscribe(name, handler)
                self._bus_handlers.append((name, handler))

    def set_var(self, key: str, value: Any) -> None:
        self.vars[key] = value

    def vars_snapshot(self) -> Dict[str, Any]:
        snap = dict(self.vars)
        snap["event"] = self._last_event
        snap["event_name"] = self._last_event_name
        snap["event_payload"] = self._last_event_payload
        if isinstance(self._last_event_payload, dict):
            for key, value in self._last_event_payload.items():
                if isinstance(key, str) and key.isidentifier():
                    snap[f"event_payload.{key}"] = value
        if isinstance(self._last_event, dict):
            for key, value in self._last_event.items():
                if isinstance(key, str) and key.isidentifier():
                    snap[f"event.{key}"] = value
        return snap

    def eval_value(self, value: Any) -> Any:
        if isinstance(value, str) and "$" in value:
            return eval_expr(value, self.vars_snapshot())
        return value

    def run_action(self, name: str, args: Dict[str, Any]) -> Any:
        fn = ActionRegistry.get(name)
        recorder_before = self._recorder
        if recorder_before:
            if name == "record_stop":
                try:
                    recorder_before.record_action(name=name, args=args or {}, result={"event": "stop"})
                except Exception:
                    pass
                return fn(self, args or {})
            try:
                result = fn(self, args or {})
                recorder_before.record_action(name=name, args=args or {}, result=result)
                return result
            except Exception as exc:
                recorder_before.record_action(name=name, args=args or {}, error=exc)
                raise

        # Allow record_start to be tracked after it attaches a recorder.
        try:
            result = fn(self, args or {})
        except Exception as exc:
            recorder_after = self._recorder
            if recorder_after:
                recorder_after.record_action(name=name, args=args or {}, error=exc)
            raise
        recorder_after = self._recorder
        if recorder_after and recorder_before is None:
            recorder_after.record_action(name=name, args=args or {}, result=result)
        return result

    def next_event(self, timeout: float = 0.1) -> Optional[str]:
        try:
            name, payload = self._event_queue.get_nowait()
            self._last_event_name = name
            self._last_event_payload = payload
            self._last_event = payload if payload is not None else name
            if self._recorder:
                self._recorder.record_event(name=str(name), payload=payload, source="bus")
            return name
        except queue.Empty:
            pass

        evt = self.channel.read_event(timeout=timeout)
        if evt is not None:
            self._last_event_name = str(evt) if not isinstance(evt, bytes) else evt.decode(errors="ignore")
            self._last_event_payload = None
            self._last_event = evt
            if self._recorder:
                payload: Any = evt
                if isinstance(evt, bytes):
                    payload = {"text": self._last_event_name, "hex": evt.hex().upper()}
                self._recorder.record_event(name=self._last_event_name or "event", payload=payload, source="channel")
            return evt
        return None

    def channel_write(self, data: bytes | str) -> None:
        self.channel.write(data)

    @property
    def recorder(self) -> Optional[ExperimentRecorder]:
        return self._recorder

    def attach_recorder(self, recorder: ExperimentRecorder) -> None:
        self._recorder = recorder
        try:
            if self._recorder_log_handler is None:
                self._recorder_log_handler = JsonlLogHandler(recorder)
                self._recorder_log_handler.setLevel(logging.INFO)
                self.logger.addHandler(self._recorder_log_handler)
        except Exception:
            pass

    def detach_recorder(self) -> None:
        if self._recorder_log_handler:
            try:
                self.logger.removeHandler(self._recorder_log_handler)
            except Exception:
                pass
        self._recorder_log_handler = None
        self._recorder = None

    def record_state(self, state_name: str) -> None:
        if self._recorder:
            self._recorder.record_state(state_name)

    def record_chart(self, payload: Dict[str, Any]) -> None:
        if self._recorder:
            self._recorder.record_chart(payload)

    def _make_bus_handler(self, name: str):
        def _handler(payload):
            self._event_queue.put((name, payload))

        return _handler

    def close(self) -> None:
        if self._recorder:
            try:
                self._recorder.close(vars_snapshot=self.vars_snapshot())
            except Exception:
                pass
            self.detach_recorder()
        if not self._bus:
            return
        for event_name, handler in self._bus_handlers:
            try:
                self._bus.unsubscribe(event_name, handler)
            except Exception:
                pass
        self._bus_handlers.clear()
