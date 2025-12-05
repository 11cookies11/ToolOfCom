"""插件示例：演示插件结构与事件订阅。"""

PLUGIN_NAME = "example_plugin"


def register(bus):
    bus.subscribe("protocol.frame", handle_frame)


def handle_frame(frame):
    # 简单示例：打印帧命令
    cmd = frame.get("cmd") if isinstance(frame, dict) else frame
    print(f"[example_plugin] 收到协议帧 cmd={cmd}")
