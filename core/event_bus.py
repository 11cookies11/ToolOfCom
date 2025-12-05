"""简单事件总线，用于解耦模块间通信。

特性：
- 订阅/取消订阅
- 发布事件时为每个回调启动独立线程，避免阻塞
- 简易日志输出，便于后续替换成正式日志框架
"""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any, Callable, DefaultDict, List

Listener = Callable[[Any], None]


class EventBus:
    def __init__(self) -> None:
        self._subs: DefaultDict[str, List[Listener]] = defaultdict(list)
        self._lock = threading.RLock()

    def subscribe(self, event_name: str, callback: Listener) -> None:
        """订阅事件。"""
        with self._lock:
            if callback not in self._subs[event_name]:
                self._subs[event_name].append(callback)
        self._log(f"subscribe -> {event_name}: {callback}")

    def unsubscribe(self, event_name: str, callback: Listener) -> None:
        """取消订阅。"""
        with self._lock:
            listeners = self._subs.get(event_name, [])
            if callback in listeners:
                listeners.remove(callback)
        self._log(f"unsubscribe -> {event_name}: {callback}")

    def publish(self, event_name: str, data: Any = None) -> None:
        """发布事件，为每个回调启动独立线程，避免阻塞主流程。"""
        with self._lock:
            listeners = list(self._subs.get(event_name, []))
        self._log(f"publish -> {event_name}, listeners={len(listeners)}, data={data!r}")

        for callback in listeners:
            thread = threading.Thread(
                target=self._safe_invoke, args=(event_name, callback, data), daemon=True
            )
            thread.start()

    def _safe_invoke(self, event_name: str, callback: Listener, data: Any) -> None:
        try:
            callback(data)
        except Exception as exc:
            self._log(f"[ERROR] callback failed: {event_name} {callback} exc={exc}")

    @staticmethod
    def _log(message: str) -> None:
        # 简易日志；后续可替换成 logging
        print(f"[EventBus] {message}")
