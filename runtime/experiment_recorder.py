from __future__ import annotations

import json
import logging
import os
import platform
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_json_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bytes):
        return {"__type__": "bytes", "hex": value.hex().upper()}
    if isinstance(value, (list, tuple)):
        return [_safe_json_value(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _safe_json_value(v) for k, v in value.items()}
    return {"__type__": type(value).__name__, "repr": repr(value)}


def _json_dumps(obj: Any) -> str:
    return json.dumps(_safe_json_value(obj), ensure_ascii=False, separators=(",", ":"))


class JsonlLogHandler(logging.Handler):
    def __init__(self, recorder: "ExperimentRecorder") -> None:
        super().__init__()
        self._recorder = recorder

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - handler side effects
        try:
            self._recorder.record_log(record)
        except Exception:
            pass


@dataclass(frozen=True)
class ExperimentPaths:
    root: Path
    meta_json: Path
    script_yaml: Path
    logs_jsonl: Path
    states_jsonl: Path
    events_jsonl: Path
    actions_jsonl: Path
    charts_jsonl: Path
    vars_snapshot_json: Path


class ExperimentRecorder:
    def __init__(
        self,
        *,
        base_dir: str | os.PathLike[str] = "logs/experiments",
        name: str = "run",
        script_text: Optional[str] = None,
        script_path: Optional[str] = None,
    ) -> None:
        self.started_at = time.time()
        self.started_at_iso = _utc_now_iso()
        self.name = name
        self.script_text = script_text
        self.script_path = script_path

        base = Path(base_dir)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        root = base / f"{ts}_{_sanitize_name(name)}"

        self.paths = ExperimentPaths(
            root=root,
            meta_json=root / "meta.json",
            script_yaml=root / "script.yaml",
            logs_jsonl=root / "logs.jsonl",
            states_jsonl=root / "states.jsonl",
            events_jsonl=root / "events.jsonl",
            actions_jsonl=root / "actions.jsonl",
            charts_jsonl=root / "charts.jsonl",
            vars_snapshot_json=root / "vars_snapshot.json",
        )

        self._fh_logs = None
        self._fh_states = None
        self._fh_events = None
        self._fh_actions = None
        self._fh_charts = None
        self._closed = False

    def start(self) -> Path:
        self.paths.root.mkdir(parents=True, exist_ok=True)
        self._write_meta()
        self._write_script()

        self._fh_logs = self.paths.logs_jsonl.open("w", encoding="utf-8", newline="\n")
        self._fh_states = self.paths.states_jsonl.open("w", encoding="utf-8", newline="\n")
        self._fh_events = self.paths.events_jsonl.open("w", encoding="utf-8", newline="\n")
        self._fh_actions = self.paths.actions_jsonl.open("w", encoding="utf-8", newline="\n")
        self._fh_charts = self.paths.charts_jsonl.open("w", encoding="utf-8", newline="\n")
        return self.paths.root

    def close(self, vars_snapshot: Optional[Dict[str, Any]] = None) -> None:
        if self._closed:
            return
        self._closed = True
        ended_at = time.time()
        try:
            self._append_jsonl(
                self._fh_logs,
                {
                    "ts": ended_at,
                    "type": "recorder",
                    "event": "stop",
                    "started_at": self.started_at,
                    "ended_at": ended_at,
                    "duration_s": ended_at - self.started_at,
                },
            )
        except Exception:
            pass
        if vars_snapshot is not None:
            try:
                self.paths.vars_snapshot_json.write_text(_json_dumps(vars_snapshot), encoding="utf-8")
            except Exception:
                pass
        for fh in [self._fh_logs, self._fh_states, self._fh_events, self._fh_actions, self._fh_charts]:
            try:
                if fh:
                    fh.flush()
                    fh.close()
            except Exception:
                pass

    def record_log(self, record: logging.LogRecord) -> None:
        payload = {
            "ts": time.time(),
            "type": "log",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        self._append_jsonl(self._fh_logs, payload)

    def record_state(self, name: str) -> None:
        payload = {"ts": time.time(), "type": "state", "name": str(name)}
        self._append_jsonl(self._fh_states, payload)

    def record_event(self, *, name: str, payload: Any, source: str) -> None:
        evt = {
            "ts": time.time(),
            "type": "event",
            "name": str(name),
            "source": str(source),
            "payload": payload,
        }
        self._append_jsonl(self._fh_events, evt)

    def record_action(self, *, name: str, args: Dict[str, Any], result: Any = None, error: Optional[BaseException] = None) -> None:
        entry: Dict[str, Any] = {
            "ts": time.time(),
            "type": "action",
            "name": str(name),
            "args": args,
        }
        if error is not None:
            entry["ok"] = False
            entry["error"] = {"type": type(error).__name__, "msg": str(error)}
        else:
            entry["ok"] = True
            entry["result"] = result
        self._append_jsonl(self._fh_actions, entry)

    def record_chart(self, payload: Dict[str, Any]) -> None:
        entry = {"ts": time.time(), "type": "chart", "payload": payload}
        self._append_jsonl(self._fh_charts, entry)

    def _write_meta(self) -> None:
        meta = {
            "name": self.name,
            "started_at": self.started_at,
            "started_at_iso": self.started_at_iso,
            "python": {"version": sys.version, "executable": sys.executable},
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
            },
            "script": {"path": self.script_path},
        }
        self.paths.meta_json.write_text(_json_dumps(meta), encoding="utf-8")

    def _write_script(self) -> None:
        if self.script_text:
            self.paths.script_yaml.write_text(self.script_text, encoding="utf-8")
            return
        if self.script_path:
            try:
                self.paths.script_yaml.write_text(Path(self.script_path).read_text(encoding="utf-8"), encoding="utf-8")
                return
            except Exception:
                pass
        self.paths.script_yaml.write_text("# script unavailable\n", encoding="utf-8")

    @staticmethod
    def _append_jsonl(fh, obj: Any) -> None:
        if fh is None:
            return
        fh.write(_json_dumps(obj) + "\n")


def _sanitize_name(name: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in str(name).strip())
    return safe[:64] if safe else "run"

