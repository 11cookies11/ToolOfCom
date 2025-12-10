"""基于 YAML 配置的轻量状态机引擎，事件主题和配置路径可参数化。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from core.event_bus import EventBus
from core.protocol_loader import ProtocolLoader
from utils.path_utils import resolve_resource_path


class FsmEngine:
    def __init__(
        self,
        bus: EventBus,
        protocol: ProtocolLoader,
        config_path: str | Path = "config/ota_fsm.yaml",
        event_prefix: str = "ota",
        frame_event: str = "protocol.frame",
        events_override: Optional[Dict[str, str]] = None,
    ) -> None:
        """FSM 引擎

        Args:
            bus: 事件总线
            protocol: 协议封帧/解析器
            config_path: 状态机 YAML 配置路径
            event_prefix: 状态机相关事件前缀（start/status/done/error/loop.*）
            frame_event: 收到协议帧的事件名
            events_override: 单独覆盖事件名的字典
        """
        self.bus = bus
        self.protocol = protocol
        self.config_path = resolve_resource_path(config_path)
        self.config: Dict[str, Any] = {}
        self.current_state: Optional[str] = None
        self._loop_break = False

        # 默认事件名，保持与以往 OTA 场景兼容，但支持定制
        self.events = {
            "start": f"{event_prefix}.start",
            "status": f"{event_prefix}.status",
            "done": f"{event_prefix}.done",
            "error": f"{event_prefix}.error",
            "loop_stop": f"{event_prefix}.loop.stop",
            "loop_finished": f"{event_prefix}.loop.finished",
            "frame": frame_event,
        }
        if events_override:
            self.events.update(events_override)

        self.load_config()
        self.bus.subscribe(self.events["start"], lambda _: self.start())
        self.bus.subscribe(self.events["frame"], self._on_frame)
        self.bus.subscribe(self.events["loop_stop"], self._set_loop_break)
        self.bus.subscribe(self.events["loop_finished"], self._set_loop_break)

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
            self.bus.publish(self.events["error"], "FSM缺少start配置")
            return
        self._enter_state(start_state)

    def _enter_state(self, state_name: str) -> None:
        states = self.config.get("states", {})
        state = states.get(state_name, {})
        self.current_state = state_name
        self.bus.publish(self.events["status"], f"STATE {state_name}")

        if state.get("exit"):
            self.bus.publish(self.events["done"])
            return

        send_cmd = state.get("send")
        if send_cmd:
            try:
                self.protocol.send(send_cmd)
            except Exception as exc:
                self.bus.publish(self.events["error"], f"发送失败 {send_cmd}: {exc}")

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
            self.bus.publish(self.events["done"])
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
            self.bus.publish(self.events["done"])

    def _set_loop_break(self, _=None) -> None:
        self._loop_break = True
