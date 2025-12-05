"""基于 YAML 配置的 OTA 状态机引擎，驱动 ProtocolLoader 发送命令。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from core.event_bus import EventBus
from core.protocol_loader import ProtocolLoader


class FsmEngine:
    def __init__(self, bus: EventBus, protocol: ProtocolLoader, config_path: str = "config/ota_fsm.yaml") -> None:
        self.bus = bus
        self.protocol = protocol
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.current_state: Optional[str] = None
        self._loop_break = False

        self.load_config()
        self.bus.subscribe("ota.start", lambda _: self.start())
        self.bus.subscribe("protocol.frame", self._on_frame)
        self.bus.subscribe("ota.loop.stop", self._set_loop_break)
        self.bus.subscribe("ota.loop.finished", self._set_loop_break)

    def load_config(self) -> None:
        if self.config_path.exists():
            with self.config_path.open("r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f) or {}
        else:
            self.config = {}

    def start(self) -> None:
        """进入初始状态。"""
        self._loop_break = False
        start_state = self.config.get("start")
        if not start_state:
            self.bus.publish("ota.error", "FSM缺少start配置")
            return
        self._enter_state(start_state)

    def _enter_state(self, state_name: str) -> None:
        states = self.config.get("states", {})
        state = states.get(state_name, {})
        self.current_state = state_name
        self.bus.publish("ota.status", f"STATE {state_name}")

        if state.get("exit"):
            self.bus.publish("ota.done")
            return

        send_cmd = state.get("send")
        if send_cmd:
            try:
                self.protocol.send(send_cmd)
            except Exception as exc:
                self.bus.publish("ota.error", f"发送失败 {send_cmd}: {exc}")

    def _on_frame(self, frame: Dict[str, Any]) -> None:
        if not self.current_state:
            return
        cmd = frame.get("cmd")
        states = self.config.get("states", {})
        state = states.get(self.current_state, {})
        wait_cmd = state.get("wait")
        if cmd != wait_cmd:
            return

        if state.get("exit"):
            self.bus.publish("ota.done")
            return

        loop = state.get("loop")
        if loop == "until_finished" and not self._loop_break:
            # 重复当前状态的发送，直到收到停止指令
            self._enter_state(self.current_state)
            return

        next_state = state.get("next")
        if next_state:
            self._enter_state(next_state)
        else:
            self.bus.publish("ota.done")

    def _set_loop_break(self, _=None) -> None:
        self._loop_break = True
