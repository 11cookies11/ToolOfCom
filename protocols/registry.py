from __future__ import annotations

from typing import Dict, Type

from protocols.base import BaseProtocol


class ProtocolRegistry:
    """协议注册表，按名称查找具体实现。"""

    _registry: Dict[str, Type[BaseProtocol]] = {}

    @classmethod
    def register(cls, name: str, protocol_cls: Type[BaseProtocol]) -> None:
        cls._registry[name] = protocol_cls

    @classmethod
    def get(cls, name: str) -> Type[BaseProtocol]:
        if name not in cls._registry:
            raise KeyError(f"未注册协议: {name}")
        return cls._registry[name]

    @classmethod
    def list(cls) -> Dict[str, Type[BaseProtocol]]:
        return dict(cls._registry)
