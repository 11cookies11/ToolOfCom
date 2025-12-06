# ToolOfCom

ToolOfCom 是面向嵌入式/工控/自动化测试的通信运行时，采用 YAML DSL + 状态机驱动，编排串口/TCP 交互、固件传输、Modbus 读写等任务。核心链路：`YAML DSL → 状态机 → 动作 (Actions) → 协议适配 → 通道 (UART/TCP)`。

## 特性一览
- 声明式 DSL：用 YAML 描述状态机流程、变量、条件、事件、超时。
- 动作系统：内置 set/log/wait/wait_for_event，支持协议动作（XMODEM、预留 Modbus），可扩展自定义动作。
- 协议适配：XMODEM/YMODEM（示例）、Modbus RTU/ASCII/TCP 封装器。
- 通道抽象：UART（pyserial）与 TCP。
- 插件式扩展：注册新动作/协议/DSL 语法即可扩展。

## 快速开始
1) 安装依赖：
```bash
pip install pyyaml
# 串口需要
pip install pyserial
```
2) 运行示例 DSL：
```bash
python dsl_main.py config/dsl_example.yaml
```
示例实现 XMODEM 固件发送的状态机：等待 "C" → 发送块 → 等 ACK/NAK → 自增块 → 发送 EOT。

## DSL 结构概览
```yaml
version: 1
vars: {...}          # 初始变量
channels: {...}      # 通道 (uart/tcp)
state_machine:
  initial: <state>
  states:
    <state_name>:
      do: [...]      # 动作列表
      on_event: {...}
      timeout: <ms>
      on_timeout: <state>
      when: <expr>
      goto: <state>
      else_goto: <state>
```
表达式支持算术/比较/逻辑，变量以 `$var` 访问，内置 `$now`（ms）、`$event`（最近事件）。

## 内置动作
- `set`: 更新变量，示例 `- set: { block: "$block + 1" }`
- `log`: 记录日志，示例 `- log: "progress $block"`
- `wait`: 休眠 ms，示例 `- wait: { ms: 500 }`
- `wait_for_event`: 阻塞等待事件，示例 `- wait_for_event: { event: "C", timeout: 2 }`

## 协议动作（示例）
- `send_xmodem_block`：发送指定块号（128B，0x1A 填充），参数 `block: "$block"`
- `send_eot`：发送 XMODEM 结束 EOT
（可扩展：Modbus 读写、YMODEM 等，参考 `actions` 目录和扩展指南）

## 通道配置示例
```yaml
channels:
  boot:
    type: uart
    device: COM5
    baudrate: 115200
  plc:
    type: tcp
    host: 192.168.1.10
    port: 502
```

## 目录结构
- `dsl/`：AST、表达式、解析器、执行器
- `actions/`：动作注册、内置动作、协议动作示例
- `protocols/`：协议适配（Modbus、X/YMODEM 等）
- `runtime/`：上下文、通道、运行器
- `config/dsl_example.yaml`：XMODEM DSL 示例
- `docs/USER_GUIDE.md`：完整用户手册

## 学习更多
请阅读 `docs/USER_GUIDE.md` 获取完整 DSL 语法、状态机详解、协议动作说明、扩展方法与最佳实践。***
