# ProtoFlow v0.4.0（草案）

对比基线：`v0.3.2..HEAD`

## 亮点
- YAML 驱动曲线窗口：在 DSL 中用 `ui.charts` 定义曲线窗口，并用 `chart_add` 推送数据点。
- 非阻塞交互控件：`ui.controls` 定义输入面板，按钮通过 EventBus 发事件，状态机用 `on_event`/`wait_for_event` 直接消费。
- 声明式单窗口布局：`ui.layout` 用 split/leaf 把 charts/controls 组合到同一个窗口里。
- 3D 散点图首版：`type: scatter3d` + `chart_add3d` 推送 3D 点（缺少 OpenGL 依赖时自动降级提示）。

## 新增功能
- DSL/AST：新增 `ui` 配置解析与 AST 节点（`ui.charts` / `ui.controls` / `ui.layout`）。
- Actions：新增 `chart_add`、`chart_add3d` 动作（GUI/Runner 启动时统一注册）。
- UI：新增曲线窗口系统（多曲线/多窗口、按 `group` 聚合、`separate` 独立窗口）。
- UI：新增交互控件窗口（float/int/bool/select + 新增 text/string 输入）。
- UI：新增布局管理器（将 charts/controls 以 YAML 布局树渲染到单窗口）。
- Charts：新增 `scatter3d` 3D 图支持（`pyqtgraph.opengl`）。

## 行为变更/改进
- 事件接入：`RuntimeContext` 支持订阅外部 EventBus 事件队列；变量快照新增 `event_name`、`event_payload`（表达式中可用 `$event_name` / `$event_payload`）。
- Demo 友好：新增 `dummy` 通道类型，适用于纯 UI/演示脚本（无实际串口/TCP 连接）。
- 依赖：`requirements.txt` 新增 `pyqtgraph>=0.13`；3D 图建议额外安装 `PyOpenGL`/`PyOpenGL_accelerate`。

## 文档与示例
- 新增英文用户指南 `docs/USER_GUIDE_EN.md`。
- 新增/更新 UI 示例脚本（charts/controls/layout）。
- 新增 `COMMIT_TEMPLATE.md`（提交模板）与 `VERSION` 文件（当前为 `v0.3.2`，发版时可同步更新）。

## 兼容性与迁移提示
- 旧 DSL 脚本不受影响：`ui` 为可选字段；未配置 `ui.layout` 时保持 charts/controls 的原有“各自独立窗口”行为。
- `ui.controls`：按钮事件名来自 `emit`，状态机通过 `on_event: { <emit>: <state> }` 获取，payload 通过 `$event.<field>` 访问。
- `scatter3d`：必须提供 `bind_x/bind_y/bind_z`；缺少 OpenGL 依赖时 UI 会提示不可用但不影响脚本运行。
