# 🚀 ToolOfCOM

🌐 Universal Communication & OTA Runtime Platform for Embedded Devices  
🧩 Protocol-Driven · Event-Flow Architecture · Pluggable Logic System

## 中文说明

### 🌟 什么是 ToolOfCOM？
ToolOfCOM 并不是普通的串口调试器，它是一种嵌入式通信运行时架构，具有：
- 🔌 多通信介质
- 📡 可配置协议 · ⚙️ FSM 驱动 OTA 升级
- 🧠 插件式逻辑扩展
- 🖥️ 图形化界面（Qt）

一句话形容它：不写通信代码，只写配置与流程，逻辑由系统执行。

### 🧱 架构核心理念
```
              UI / MainWindow
  图形界面只负责展示，不参与逻辑或协议处理
                     ▲
                     │
                  EventBus
  系统总线，负责事件分发、行为触发、数据流转
                     ▲
        ┌───────────┴───────────┐
        │                       │
  ProtocolLoader         PluginManager
  协议解释器             逻辑扩展系统
        │                       │
        └───────┬───────┬───────┘
                │       │
           FSM Engine   │         CommunicationManager
    升级流程完全由 YAML 驱动     串口 / TCP 等统一入口
                │                       │
         SerialSession               TcpSession
    实体设备                       虚拟 MCU / Renode
```

### ✅ 这意味着什么？
| 概念 | 在旧工具里的通信 | ToolOfCOM |
| --- | --- | --- |
| 协议 | 写死在代码里 | YAML 配置 |
| 升级流程 | if/else | 有限状态机 FSM |
| 扩展性 | 几乎没有 | 插件无限扩展 |

### ⚡ 核心能力亮点
| 功能 | 描述 |
| --- | --- |
| 🔌 多通道通信 | 串口 UART / TCP / 未来蓝牙 CAN 都能接入 |
| 📡 协议可配置 | header / length / CRC / command 都写在 YAML |
| 🔁 事件循环架构 | 每一步操作都是事件，而不是函数调用 |
| ⚙️ FSM OTA 引擎 | 升级逻辑通过状态机执行，而不是写死 |
| 🧩 插件系统 | 想加能力？写个插件就行 |
| 🖥️ GUI 界面 | 不需要命令行，所有行为一目了然 |
| 🚀 OTA 升级体验 | 从“手写流程”变成“写 YAML 让系统跑” |

### 🧭 使用场景
- 💡 BootLoader 升级
- 🛠️ 嵌入式调试实验室
- 📦 生产线批量烧录
- 🌐 多设备运营 & 远程升级
- 🧪 Renode 虚拟 MCU 测试环境

### 🎯 为什么它与众不同？
因为它击穿了嵌入式调试的“三大魔咒”：
| 障碍 | 传统方式 | ToolOfCOM |
| --- | --- | --- |
| 协议变动 | 改代码改配置通信变化 | 推倒重来？交给 Session |
| 逻辑扩展 | 重写流程 | 写插件 |

它的本质不是工具，而是：**Embedded Device Runtime System** —— 是嵌入式通信界的 Node.js + Nginx + HomeAssistant 混合体。

### 📈 项目定位进化轨迹
- v1.0  单设备通信与 OTA
- v2.0  多设备并行管理
- v3.0  分布式远程设备运营平台
- vX.X  嵌入式设备生态运行时



### 📝 一句总结
ToolOfCOM 不是调试器，而是嵌入式设备行为执行引擎。它让 MCU 不是被操作，而是被编排。
