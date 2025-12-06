from __future__ import annotations

import argparse
import logging
import socket
import sys
import time
from pathlib import Path
from typing import Any, Dict

import yaml

from actions import modbus_request, xmodem_send, ymodem_send
from protocols import modbus_ascii, modbus_rtu, modbus_tcp, xmodem, ymodem  # noqa: F401 触发注册

try:
    import serial
except ImportError:  # pragma: no cover
    serial = None


class BaseChannel:
    def write(self, data: bytes | str) -> None:  # pragma: no cover - 接口
        raise NotImplementedError()

    def read(self, size: int = 1, timeout: float = 1.0) -> bytes:  # pragma: no cover - 接口
        raise NotImplementedError()

    def read_until(self, terminator: bytes, timeout: float = 1.0) -> bytes:
        buf = bytearray()
        deadline = time.time() + timeout
        while time.time() < deadline:
            chunk = self.read(1, timeout=max(0.01, deadline - time.time()))
            if chunk:
                buf.extend(chunk)
                if buf.endswith(terminator):
                    break
            else:
                time.sleep(0.01)
        return bytes(buf)

    def close(self) -> None:  # pragma: no cover - 接口
        pass


class SerialChannel(BaseChannel):
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1.0) -> None:
        if serial is None:
            raise ImportError("pyserial 未安装，无法创建串口通道")
        self.ser = serial.Serial(port=port, baudrate=baudrate, timeout=0)
        self._timeout = timeout

    def write(self, data: bytes | str) -> None:
        payload = data.encode() if isinstance(data, str) else data
        self.ser.write(payload)

    def read(self, size: int = 1, timeout: float = 1.0) -> bytes:
        deadline = time.time() + timeout
        buf = bytearray()
        while len(buf) < size and time.time() < deadline:
            chunk = self.ser.read(size - len(buf))
            if chunk:
                buf.extend(chunk)
            else:
                time.sleep(0.01)
        return bytes(buf)

    def close(self) -> None:
        try:
            self.ser.close()
        except Exception:
            pass


class TcpChannel(BaseChannel):
    def __init__(self, host: str, port: int, timeout: float = 2.0) -> None:
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(0.5)

    def write(self, data: bytes | str) -> None:
        payload = data.encode() if isinstance(data, str) else data
        self.sock.sendall(payload)

    def read(self, size: int = 1, timeout: float = 1.0) -> bytes:
        deadline = time.time() + timeout
        buf = bytearray()
        while len(buf) < size and time.time() < deadline:
            try:
                chunk = self.sock.recv(size - len(buf))
                if chunk:
                    buf.extend(chunk)
                else:
                    time.sleep(0.01)
            except socket.timeout:
                continue
        return bytes(buf)

    def close(self) -> None:
        try:
            self.sock.close()
        except Exception:
            pass


ACTIONS = {
    "modbus_request": modbus_request.run,
    "xmodem_send": xmodem_send.run,
    "ymodem_send": ymodem_send.run,
}


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_channels(config: Dict[str, Any]) -> Dict[str, BaseChannel]:
    channels_cfg = config.get("channels") or config.get("app", {}).get("channels", {})
    channels: Dict[str, BaseChannel] = {}
    for name, cfg in channels_cfg.items():
        ctype = str(cfg.get("type", "serial")).lower()
        if ctype == "serial":
            channels[name] = SerialChannel(
                port=cfg["port"],
                baudrate=int(cfg.get("baudrate", 115200)),
                timeout=float(cfg.get("timeout", 1.0)),
            )
        elif ctype == "tcp":
            channels[name] = TcpChannel(
                host=cfg["host"],
                port=int(cfg["port"]),
                timeout=float(cfg.get("timeout", 2.0)),
            )
        else:
            raise ValueError(f"不支持的通道类型: {ctype}")
    return channels


def run_tasks(tasks: list[Dict[str, Any]], channels: Dict[str, BaseChannel], logger: logging.Logger) -> None:
    for idx, task in enumerate(tasks):
        action = task.get("action")
        runner = ACTIONS.get(action)
        if not runner:
            raise ValueError(f"未知 action: {action}")
        logger.info(f"执行任务 {idx + 1}/{len(tasks)}: {action}")
        result = runner(task, channels, logger)
        logger.info(f"任务完成 {action}: {result}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ToolOfCom 通信运行时")
    parser.add_argument(
        "-c", "--config", default="config/app.yaml", help="任务 YAML 路径，默认 config/app.yaml"
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger("runtime")

    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"配置不存在: {config_path}")
        return 2

    config = load_yaml(config_path)
    tasks = config.get("tasks") or config.get("app", {}).get("tasks", [])
    if not tasks:
        logger.warning("未在 YAML 中找到 tasks，退出")
        return 0

    channels: Dict[str, BaseChannel] = {}
    try:
        channels = build_channels(config)
        run_tasks(tasks, channels, logger)
        return 0
    except Exception as exc:
        logger.exception("运行时异常: %s", exc)
        return 1
    finally:
        for ch in channels.values():
            try:
                ch.close()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
