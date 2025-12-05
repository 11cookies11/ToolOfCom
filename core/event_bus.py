"""简单事件总线，用于解耦模块间通信。"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, DefaultDict, List

Listener = Callable[[Any], None]


class EventBus:
    def __init__(self) -> None:
        self._subs: DefaultDict[str, List[Listener]] = defaultdict(list)

    def subscribe(self, topic: str, listener: Listener) -> None:
        self._subs[topic].append(listener)

    def publish(self, topic: str, payload: Any = None) -> None:
        for listener in list(self._subs.get(topic, [])):
            try:
                listener(payload)
            except Exception:
                # 生产环境可接入日志
                pass
