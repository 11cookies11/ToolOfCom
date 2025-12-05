# ToolOfCOM
[English](#english-version) | [中文](#中文说明)

## 中文说明

### 概述
ToolOfCOM 是一个事件驱动的通信与 OTA 工具，支持串口/TCP 通道、协议帧解析、插件扩展与 Qt 界面。核心依赖 `pyserial`、`PySide6`/`PyQt6`、`pywin32`、`PyYAML`。

### 目录结构
```
ToolOfCOM/
 ├── core/                      # 核心模块
 │    ├── event_bus.py          # 事件总线
 │    ├── communication_manager.py # 统一通信入口，转发 comm.*
 │    ├── serial_manager.py     # 串口会话
 │    ├── tcp_session.py        # TCP 会话
 │    ├── protocol_loader.py    # 协议装载/帧解析/CRC
 │    ├── fsm_engine.py         # OTA 状态机（配置驱动）
 │    └── plugin_manager.py     # 插件加载
 ├── ui/
 │    └── main_window.py        # Qt 主界面，选择串口/TCP、发送与日志
 ├── config/
 │    ├── protocol.yaml         # 帧格式、命令定义
 │    ├── ota_fsm.yaml          # OTA 状态机配置
 │    └── app.yaml              # 预留
 ├── plugins/
 │    ├── example_plugin.py
 │    └── ota_upgrade.py        # OTA 发送示例
 ├── assets/icons/              # 资源占位
 ├── src/com_tool.py            # COM 调试脚本
 └── main.py                    # 应用入口
```

### 快速开始
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
$env:NO_PROXY='*'; $env:PIP_NO_PROXY='*'; $env:HTTP_PROXY=''; $env:HTTPS_PROXY='';
python -m pip install -r requirements.txt
python .\main.py
```
若需调试 COM 组件：
```powershell
python .\src\com_tool.py --prog-id "Your.ProgID" --method "Ping" --args "hello"
```

### 事件流与协作
- `CommunicationManager` 统一串口/TCP 选择与发送，输出 `comm.rx/tx/connected/disconnected/error`。
- `ProtocolLoader` 订阅 `serial.rx`，发布 `protocol.frame`，`send` 时发布 `protocol.tx`（由 CommunicationManager 转发发送）。
- `FsmEngine` 订阅 `ota.start` 与 `protocol.frame`，按 `ota_fsm.yaml` 迁移，结束发布 `ota.done`。
- 插件通过 `PluginManager` 动态加载，订阅 bus 事件扩展功能（如 `plugins/ota_upgrade.py`）。

### 配置
- `config/protocol.yaml`：header/tail/crc/max_length、commands 定义。
- `config/ota_fsm.yaml`：配置状态机字段 `send/wait/next/loop/exit`，可按设备协议修改。

### 插件开发
在 `plugins/your_plugin.py` 中：
```python
PLUGIN_NAME = "your_plugin"
def register(bus, protocol=None):
    bus.subscribe("protocol.frame", handler)
```
加载成功发布 `plugin.loaded`，异常发布 `plugin.error`。

### OTA 流程示例
- UI 或插件触发 `ota.start`。
- `FsmEngine` 按配置驱动 `ProtocolLoader.send`，回包触发 `protocol.frame` 继续迁移。
- `plugins/ota_upgrade.py` 提供写块示例，发布 `ota.status/finished/error` 供 UI 展示。

### 常见问题
- Qt 未安装：`python -m pip install "PySide6>=6.6"`（或 PyQt6）。
- 代理报错 `check_hostname requires server_hostname`：清空空代理或设置正确的 `HTTP_PROXY/HTTPS_PROXY`。
- 串口权限/位数：Python 与目标 COM/驱动需位数匹配，必要时以管理员运行。

---

## English Version

### Overview
ToolOfCOM is an event-driven communication and OTA tool with serial/TCP channels, protocol framing/parsing, plugin system, and a Qt UI. Core deps: `pyserial`, `PySide6`/`PyQt6`, `pywin32`, `PyYAML`.

### Project Layout
```
ToolOfCOM/
 ├── core/                      # Core modules
 │    ├── event_bus.py          # Event bus
 │    ├── communication_manager.py # Unified comm entry, emits comm.*
 │    ├── serial_manager.py     # Serial session
 │    ├── tcp_session.py        # TCP session
 │    ├── protocol_loader.py    # Protocol framing/parsing/CRC
 │    ├── fsm_engine.py         # Config-driven OTA FSM
 │    └── plugin_manager.py     # Plugin loader
 ├── ui/main_window.py          # Qt UI for Serial/TCP, send & log
 ├── config/protocol.yaml       # Frame format, commands
 ├── config/ota_fsm.yaml        # OTA state machine config
 ├── plugins/                   # Plugins (OTA example, frame logger)
 ├── assets/icons/              # Assets placeholder
 ├── src/com_tool.py            # COM debug helper
 └── main.py                    # Entry point
```

### Quick Start
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
$env:NO_PROXY='*'; $env:PIP_NO_PROXY='*'; $env:HTTP_PROXY=''; $env:HTTPS_PROXY='';
python -m pip install -r requirements.txt
python .\main.py
```
COM debug (optional):
```powershell
python .\src\com_tool.py --prog-id "Your.ProgID" --method "Ping" --args "hello"
```

### Event Flow & Collaboration
- `CommunicationManager` unifies Serial/TCP selection and sending, emits `comm.rx/tx/connected/disconnected/error`.
- `ProtocolLoader` listens to `serial.rx`, emits `protocol.frame`; `send` emits `protocol.tx` (sent by CommunicationManager).
- `FsmEngine` listens to `ota.start` and `protocol.frame`, drives FSM from `ota_fsm.yaml`, finishes with `ota.done`.
- Plugins loaded by `PluginManager` subscribe to bus events (e.g., `plugins/ota_upgrade.py`).

### Config
- `config/protocol.yaml`: header/tail/crc/max_length, command defs.
- `config/ota_fsm.yaml`: FSM fields `send/wait/next/loop/exit`; adjust to your device protocol.

### Plugin Development
Create `plugins/your_plugin.py`:
```python
PLUGIN_NAME = "your_plugin"
def register(bus, protocol=None):
    bus.subscribe("protocol.frame", handler)
```
On success `plugin.loaded` is published; errors emit `plugin.error`.

### OTA Example
- UI or plugin fires `ota.start`.
- `FsmEngine` drives `ProtocolLoader.send`; device responses trigger `protocol.frame` for next transitions.
- `plugins/ota_upgrade.py` writes blocks and emits `ota.status/finished/error` for UI.

### FAQ
- Missing Qt: `python -m pip install "PySide6>=6.6"` (or PyQt6).
- Proxy error `check_hostname requires server_hostname`: clear empty proxies or set valid `HTTP_PROXY/HTTPS_PROXY`.
- Serial permissions/bitness: match Python and device bitness; run as admin if needed.
