# ToolOfCom

一个用 Python 调用 Windows COM 组件的最小脚手架，包含依赖清单、示例脚本以及基础使用说明。

## 先决条件
- Windows 环境（COM 仅在 Windows 可用）
- Python 3.9+（建议与目标 COM 组件的位数一致：32/64 位）
- 能访问目标 COM 组件（已注册的 `ProgID` 或 CLSID）

## 快速开始
1) 创建并激活虚拟环境（PowerShell）：
```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
```
2) 安装依赖：
```powershell
pip install -r requirements.txt
```
3) 配置环境变量（可选）：在项目根目录创建 `.env`，示例：
```
COM_PROG_ID=Your.ProgID
COM_VISIBLE=1
```
4) 运行示例脚本：
```powershell
python .\\src\\com_tool.py --prog-id "Your.ProgID" --method "Ping" --args "hello" "world"
```

## 示例脚本说明
`src/com_tool.py` 提供一个可扩展的入口：
- 通过 `--prog-id` 指定 COM 组件（ProgID 或 CLSID）
- 通过 `--method` 指定要调用的方法名；`--args` 传入位置参数
- 自动加载 `.env`（使用 `python-dotenv`），便于在本地保存默认 ProgID 等配置

## 常见问题
- **位数不匹配**：Python 与 COM 组件需同为 32 位或 64 位，否则会 `CoCreateInstance` 失败。
- **注册问题**：确保 COM 组件已正确注册（通常为 `regsvr32 xxx.dll` 或安装程序完成注册）。
- **权限问题**：部分组件需要以管理员运行或在提升权限的 PowerShell 中注册。

## 后续扩展建议
- 为常用方法封装友好的 Python API（而不是裸调用 `Dispatch`）
- 增加日志与异常捕获，写入文件或事件日志
- 如需长时运行，可加入健康检查、心跳或重试策略
