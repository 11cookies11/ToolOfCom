<p align="center">
  <img src="./docs/pictures/logo.png" width="200" alt="ToolOfCom logo"/>
</p>

<p align="center">
  <b>别再发送字节了，开始执行协议。</b>
</p>

<p align="center">
ToolOfCom 是一个通信运行时引擎，让 UART / TCP / Modbus / XMODEM 的交互流程不再是零散的收发字节，而是可编排、可执行的协议工作流。
</p>

---

[EN](./README_EN.md)

<p align="center">
  <a href="https://github.com/11cookies11/ToolOfCom/actions/workflows/ci.yml"><img alt="build" src="https://img.shields.io/github/actions/workflow/status/11cookies11/ToolOfCom/ci.yml?branch=main&label=build&style=for-the-badge"/></a>
  <a href="https://github.com/11cookies11/ToolOfCom/tags"><img alt="version" src="https://img.shields.io/github/v/tag/11cookies11/ToolOfCom?label=version&style=for-the-badge"/></a>
  <a href="./LICENSE"><img alt="license" src="https://img.shields.io/github/license/11cookies11/ToolOfCom?style=for-the-badge"/></a>
  <img alt="platform" src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux-orange?style=for-the-badge"/>
  <img alt="language" src="https://img.shields.io/badge/language-Python%20%2B%20Qt-7F3FBF?style=for-the-badge"/>
</p>

## 🌐 项目简介（Overview）

ToolOfCOM 不是一个“串口助手”，它是一套 **通信逻辑运行时**。
 传统调试工具只能一次性收发数据，而 ToolOfCOM 可以通过 DSL 描述完整通信流程，并由状态机执行器驱动协议逻辑，实现**可配置、可编排、可扩展的通信行为**。

```lua
                                            ┌──────────┐
                                            │ YAML DSL │  ← 人类可读的通信与行为描述
                                            └─────┬────┘
                                                  ↓
                                            ┌──────────┐
                                            │   AST    │  ← 结构化语义树（协议/状态/事件/动作）
                                            └─────┬────┘
                                                  ↓
                                            ┌──────────┐
                                            │ Executor │  ← 在 PC/MCU 上解释执行
                                            └──────────┘

```

传统串口或通信工具的核心能力只有一件事：
发送一些字节，然后等待回应。


但真实的设备通信从不是单次发送，而是完整的协议流程：

- 握手与协商  
- 多帧数据交互  
- CRC 校验  
- 重试与超时处理  
- 条件跳转与流程驱动  
- 最终执行动作

**ToolOfCom 重新定义了通信方式**：

你不再写脚本，也不再依赖 GUI 点点点，而是通过 DSL 描述协议行为，由运行时引擎自动执行通信流程。

换句话说：

通信 → 不再是动作
通信 → 是状态驱动的执行逻辑


---



## 🤔 为什么要做 ToolOfCom？

现有通信工具存在几个本质问题：

| 痛点 | 现状 |
|------|------|
| 操作层次过低 | 停留在字节收发层面 |
| 协议逻辑脆弱 | 通过脚本或人工操作维持 |
| 无状态 | 无法正确表达协议的流程与条件 |
| 难扩展 | 每种协议都要重新写代码 |

通信世界其实是「状态机」，不是「一次性指令」。  
ToolOfCom 的价值在于：

+ 将协议逻辑 → 声明式 DSL
+ 将通信流程 → 状态机执行器
+ 将设备交互 → 可编排工作流


**从此，协议不是代码，而是数据。**

---



## 🚀 核心特性（Features）

| 特性 | 描述 |
|------|------|
| 🧩 声明式 DSL | 用 YAML 描述通信流程，而不是写脚本 |
| 🔁 状态机运行时 | 自动执行收发、等待、跳转、重试等逻辑 |
| 🔌 协议驱动层 | UART / TCP / Modbus / XMODEM / 自定义协议 |
| 🧱 分层架构 | 通道、协议、动作完全解耦 |
| ⏱ 可控执行 | 无随机等待，全流程可预测 |
| 🪢 可扩展注册表 | 自定义协议行为无需修改核心代码 |
| 📡 多设备并行 | 支持 orchestrate 多通道工作流 |

---



## 🧱 架构设计（Architecture）

```lua
                                           +----------------+
                                           |   Workflow     |  <-- YAML DSL
                                           +----------------+
                                                    |
                                                    v
                                          +---------------------+
                                          |  State Machine Core |
                                          +---------------------+
                                           /        |        \
                                          v         v         v
                                    +---------+ +---------+ +---------+
                                    | Driver |  | Driver |  | Driver   | <-- Modbus / XMODEM / TCP / UART
                                    +---------+ +---------+ +---------+
                                                    |
                                                    v
                                                +---------+
                                                | Channel | <-- 串口/网络/自定义端口
                                                +---------+

```

**通信不再以“发送什么”为中心  
而是以“下一步应该发生什么”为中心。**

---



## 📝 DSL 示例（Example）

```yaml
version: 1		#可配合BootAppOfRAM仓库代码进行测试

vars:
  block: 1
  file_path: ./logs/app.bin      # firmware BIN path
  max_blocks: 960           # 120 KB / 128B
  retry: 0                  # current retry count
  max_retry: 5              # max retries per block before abort

channels:
  boot:
    type: tcp
    host: 192.168.31.135    # Renode UART bridge host
    port: 4321              # Renode UART bridge port
    baudrate: 19200         # baudrate hint if using a serial bridge
    timeout: 10             # connection timeout seconds
    log_path: ./logs/boot_uart.log

state_machine:
  initial: wait_handshake
  states:
    wait_handshake:
      do:
        - log: "waiting for 'C' from bootloader (XMODEM-CRC handshake)"
      on_event:
        "C": send_block
      timeout: 10000
      on_timeout: fail

    send_block:
      do:
        - action: send_xmodem_block
          args:
            block: "$block"
        - wait: { ms: 50 }        # inter-packet gap to allow device processing
      on_event:
        "\x06": next_block      # ACK
        "\x15": resend_block    # NAK
        "\x18": abort           # CAN (size overflow or fatal error)
      timeout: 5000
      on_timeout: resend_block

    resend_block:
      do:
        - set: { retry: "$retry + 1" }
        - log: "resend block"
      when: "$retry < $max_retry"
      goto: send_block
      else_goto: abort

    next_block:
      do:
        - set: { block: "$block + 1" }
        - set: { retry: 0 }
      when: "$block <= $file_block_count and $block <= $max_blocks"
      goto: send_block
      else_goto: send_eot

    send_eot:
      do:
        - action: send_eot
      on_event:
        "\x06": done            # ACK
        "\x18": abort
      timeout: 5000
      on_timeout: abort

    abort:
      do:
        - log: "bootloader returned CAN or timeout, stop transfer"
      goto: done

    fail:
      do:
        - log: "handshake timeout, XMODEM not started"
      goto: done

    done:
      do:
        - log: "XMODEM flow ended (boot should jump on success)"

```

**没有 Python，没有回调，没有 if-else**
 通信逻辑变成声明式流。

---



⚡ 快速开始（Quick Start）

+ release版本可以直接运行(未测试Liunx版本)

---



## 🔌 已支持协议（Supported Protocols）

| 协议           | 状态 |
| -------------- | ---- |
| UART           | ✔️    |
| TCP            | ✔️    |
| Modbus RTU     | ✔️    |
| XMODEM         | ✔️    |
| 自定义协议插件 | ✔️    |

---



## 🛣 开发路线图（Roadmap）

-  Web 可视化流程编辑器
-  二进制数据传输增强
-  固件更新模板
-  MQTT 适配层
-  设备拓扑与发现功能

------



## 🤝 参与贡献（Contribute）

欢迎提交 PR、Issue，以及协议扩展插件。
ToolOfCOM 的长期目标是成为 **通信协议的执行层**。

---



## 📄 许可证（License）

This project is licensed under the MIT License.  
See the [LICENSE](./LICENSE) file for details.

---



## 📚 了解更多（Learn More）

**详见 `docs/USER_GUIDE.md`，包含完整 DSL 语法、状态机语义、协议动作、扩展方式与最佳实践。**
