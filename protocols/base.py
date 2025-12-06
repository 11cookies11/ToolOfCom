from __future__ import annotations

import logging
from typing import Any


class BaseProtocol:
    """协议基类：所有协议实现都应继承并覆盖 execute。"""

    def __init__(self, channel: Any, logger: logging.Logger | None = None) -> None:
        self.channel = channel
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def execute(self, **kwargs):  # pragma: no cover - 接口定义
        raise NotImplementedError()

    def _log(self, level: str, message: str) -> None:
        """兼容 logger/info/warning/error，缺省退回 print。"""
        log_fn = getattr(self.logger, level, None)
        if callable(log_fn):
            log_fn(message)
        else:
            print(f"[{self.__class__.__name__}] {message}")
