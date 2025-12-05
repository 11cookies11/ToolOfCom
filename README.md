# ToolOfCOM

一个用 Python 调用 Windows COM 组件的脚手架，并提供桌面工具的基础目录结构。

## 目录结构
```
ToolOfCOM/
 ├── core/
 │    ├── event_bus.py         # 事件总线
 │    ├── serial_manager.py    # 串口管理
 │    ├── protocol_loader.py   # 协议装载器
 │    └── plugin_manager.py    # 插件机制
 ├── ui/
 │    ├── main_window.py       # 主界面
 │    └── widgets/             # 独立控件区
 ├── config/
 │    ├── protocol.yaml        # 指令、帧格式、CRC等定义
 │    └── app.yaml             # 全局配置、自更新策略
 ├── plugins/
 │    ├── example_plugin.py    # 功能扩展示例
 ├── assets/
 │    └── icons/               # 图标资源
 ├── main.py                   # 入口
 └── src/com_tool.py           # COM 调试脚本
```

## 快速开始
1) 创建并激活虚拟环境（PowerShell）：
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
2) 安装依赖（如遇代理问题，可设置 `NO_PROXY='*'`）：
```powershell
$env:NO_PROXY='*'; $env:PIP_NO_PROXY='*'; $env:HTTP_PROXY=''; $env:HTTPS_PROXY='';
python -m pip install -r requirements.txt
```
3) 配置环境变量（可选）：在项目根目录创建 `.env`，示例：
```
COM_PROG_ID=Your.ProgID
COM_VISIBLE=1
```
4) 调试 COM：
```powershell
python .\src\com_tool.py --prog-id "Your.ProgID" --method "Ping" --args "hello" "world"
```

## 模块说明
- `core/`：事件总线、串口管理（需接入 pyserial）、协议装载（YAML）、插件发现加载。
- `ui/`：界面层占位；根据所选 GUI 框架填充。
- `config/`：协议与应用配置示例 YAML。
- `plugins/`：插件示例，演示扩展点。
- `main.py`：应用入口，初始化核心组件并展示 UI。

## 后续扩展建议
- 在 `serial_manager.py` 引入 `pyserial` 完成收发与线程安全。
- 在 `protocol_loader.py` 增加 CRC/帧封装与校验。
- 在 `plugin_manager.py` 引入接口约束（如抽象基类）与错误日志。
- 在 `ui/main_window.py` 根据框架实现实际界面逻辑与事件绑定。
