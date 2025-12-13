<p align="center">
  <img src="./docs/pictures/logo.png" width="200" alt="ProtoFlow logo"/>
</p>

<p align="center">
  <b>Stop sending bytes. Start executing protocols.</b>
</p>
<p align="center">
ProtoFlow is a communication runtime engine that transforms UART / TCP / Modbus / XMODEM interactions from scattered byte operations into programmable and executable protocol workflows.
</p>


---

[中文](./README.md)

<p align="center">
  <a href="https://github.com/11cookies11/ProtoFlow/actions/workflows/ci.yml"><img alt="build" src="https://img.shields.io/github/actions/workflow/status/11cookies11/ProtoFlow/ci.yml?branch=main&label=build&style=for-the-badge"/></a>
  <a href="https://github.com/11cookies11/ProtoFlow/tags"><img alt="version" src="https://img.shields.io/github/v/tag/11cookies11/ProtoFlow?label=version&style=for-the-badge"/></a>
  <a href="./LICENSE"><img alt="license" src="https://img.shields.io/github/license/11cookies11/ProtoFlow?style=for-the-badge"/></a>
  <img alt="platform" src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux-orange?style=for-the-badge"/>
  <img alt="language" src="https://img.shields.io/badge/language-Python%20%2B%20Qt-7F3FBF?style=for-the-badge"/>
</p>

## 🌐 Overview

ProtoFlow is not a “serial assistant” tool — it is a **communication logic runtime**.

Traditional debugging tools can only send and receive raw bytes. ProtoFlow, however, describes complete communication flows using a DSL and executes them through a state-machine runtime, enabling **configurable, orchestrated, and extensible protocol behaviors**.

```lua
                                ┌──────────┐
                                │ YAML DSL │  ← Human-readable description of communication logic
                                └─────┬────┘
                                      ↓
                                ┌──────────┐
                                │   AST    │  ← Structured semantic tree (protocol/state/event/action)
                                └─────┬────┘
                                      ↓
                                ┌──────────┐
                                │ Executor │  ← Runtime on PC / MCU
                                └──────────┘
```

Traditional serial or communication tools focus on only one thing:

**Send some bytes, then wait.**

But real device communication is never a single request–response action.
 It is a **protocol lifecycle**, including:

- Handshake and negotiation
- Multi-frame data exchange
- CRC validation
- Retries and timeout handling
- Conditional branching and execution flow
- Final actions and transitions

**ProtoFlow redefines communication**:

You no longer write scripts or click UI buttons.
 You describe protocol behaviors declaratively using DSL,
 and the runtime engine executes the communication flow automatically.

In other words:

```
Communication → no longer an operation
Communication → becomes state-driven executable logic
```

## 🤔 Why ProtoFlow?

Existing communication tools suffer from fundamental limitations:

| Pain Point         | Current Situation                          |
| ------------------ | ------------------------------------------ |
| Low abstraction    | Stuck at byte-level operations             |
| Fragile logic      | Maintained through scripts or manual input |
| Stateless          | Cannot express protocol sequences          |
| Poor extensibility | Each new protocol requires new code        |

The communication world is inherently a **state machine**, not a collection of byte dumps.

ProtoFlow unlocks:

- Protocol logic → declarative DSL
- Communication sequence → state-machine executor
- Device interaction → orchestrated workflow

**From now on, protocols are not code — they are data.**

------

## 🚀 Features

| Feature             | Description                                         |
| ------------------- | --------------------------------------------------- |
| 🧩 Declarative DSL   | Describe communication flows in YAML, no scripting  |
| 🔁 State runtime     | Executes send/receive, wait, branching, retry…      |
| 🔌 Protocol layer    | UART / TCP / Modbus / XMODEM / Custom protocols     |
| 🧱 Layered design    | Channels, drivers, and actions fully decoupled      |
| ⏱ Deterministic     | No uncertain waits; predictable execution path      |
| 🪢 Extensible        | Register custom actions without modifying core code |
| 📡 Multi-device flow | Orchestrate workflows across multiple channels      |

------

## 🧱 Architecture

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
                                    | Driver  | | Driver  | | Driver   | <-- Modbus / XMODEM / TCP / UART
                                    +---------+ +---------+ +---------+
                                                    |
                                                    v
                                                +---------+
                                                | Channel | <-- Serial / Network / Custom endpoint
                                                +---------+

**Communication is no longer about “what to send”,
 but about “what should happen next”.**

------

## 📝 YAML Demos

This repo includes several runnable DSL YAML demos (the full YAML is not in README to keep it short):

- `config/chart_demo.yaml`: chart windows (`ui.charts`), multi-window via `group/separate`; pushes points with `chart_add`.
- `config/controls_demo.yaml`: non-blocking controls (`ui.controls`), input panel + button `emit` events; access payload via `$event.<field>`.
- `config/layout_demo.yaml`: declarative layout (`ui.layout`), split a single window with charts/controls; includes `scatter3d` + `chart_add3d`.
- `charts_example.yaml`: minimal `ui.charts`; preview via `python charts_main.py charts_example.yaml` (random data).

How to run:
- GUI: `python main.py` → Script mode → load/paste YAML → Run
- CLI (no GUI): `python dsl_main.py <yaml>` (no charts/controls visualization)

**No Python, no callbacks, no if-else statements.**

Communication logic becomes a **declarative execution flow**.

------

## ⚡ Quick Start

Download the release and run directly.
 (Linux version currently unverified.)

------

## 🔌 Supported Protocols

| Protocol        | Status |
| --------------- | ------ |
| UART            | ✔️      |
| TCP             | ✔️      |
| Modbus RTU      | ✔️      |
| XMODEM          | ✔️      |
| Custom Protocol | ✔️      |

------

## 🛣 Roadmap

- Web-based visual flow editor
- Enhanced binary data transfer
- Firmware update templates
- MQTT adapter layer
- Device topology and discovery

------

## 🤝 Contribute

PRs, issues, and protocol extension plugins are warmly welcome.
 The long-term goal of ProtoFlow is to become the **execution layer of communication protocols**.

------

## 📄 License

This project is licensed under the MIT License.  
See the [LICENSE](./LICENSE) file for details.

------



## Learn More

See `docs/USER_GUIDE.md` for the full DSL grammar, state-machine semantics, protocol actions, extension methods, and best practices.
