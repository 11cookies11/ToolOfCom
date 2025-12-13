from __future__ import annotations

from typing import Dict, Iterable, List, Optional

try:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtWidgets import QMainWindow, QSplitter, QVBoxLayout, QWidget, QLabel
except ImportError:  # pragma: no cover
    from PyQt6.QtCore import Qt, QTimer  # type: ignore
    from PyQt6.QtWidgets import QMainWindow, QSplitter, QVBoxLayout, QWidget, QLabel  # type: ignore

from dsl.ast_nodes import ChartSpec, ControlSpec, LayoutNode
from ui.charts.chart_widget import ChartWidget
from ui.charts.chart_widget_3d import Chart3DWidget
from ui.controls.control_window import ControlWidget


class LayoutWindow(QMainWindow):
    """Single window hosting a layout tree of charts/controls."""

    def __init__(self, root_widget: QWidget, title: str = "Layout") -> None:
        super().__init__()
        self.setWindowTitle(title)
        self.setCentralWidget(root_widget)


class LayoutManager:
    """Builds layout tree into a single window and routes chart data."""

    def __init__(
        self,
        root: LayoutNode,
        chart_specs: Iterable[ChartSpec],
        control_specs: Iterable[ControlSpec],
        bus=None,
        title: str = "Layout",
    ) -> None:
        self.root = root
        self.bus = bus
        self.chart_specs = {c.id: c for c in chart_specs}
        self.control_specs = {c.id: c for c in control_specs}
        self.chart_widgets: Dict[str, ChartWidget] = {}
        self.control_widgets: Dict[str, ControlWidget] = {}
        self.bind_map: Dict[str, List[ChartWidget]] = {}
        self.scatter_specs: Dict[str, List[tuple[str, str, str, Chart3DWidget]]] = {}

        root_widget = self._build_widget(root)
        self.window = LayoutWindow(root_widget, title=title)
        self.window.show()
        self.timer = QTimer(self.window)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    def _build_widget(self, node: LayoutNode) -> QWidget:
        if node.type == "split":
            orientation = Qt.Horizontal if (node.orientation or "horizontal") == "horizontal" else Qt.Vertical
            splitter = QSplitter(orientation)
            for child in node.children:
                splitter.addWidget(self._build_widget(child))
            return splitter

        # Leaf: create a container with the requested widgets
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        for cid in node.charts:
            spec = self.chart_specs.get(cid)
            if not spec:
                layout.addWidget(QLabel(f"Unknown chart: {cid}"))
                continue
            widget: QWidget
            if getattr(spec, "chart_type", "line") == "scatter3d":
                widget = Chart3DWidget(title=spec.title, max_points=spec.max_points)
                if spec.bind_x and spec.bind_y and spec.bind_z:
                    self.scatter_specs.setdefault(cid, []).append((spec.bind_x, spec.bind_y, spec.bind_z, widget))  # type: ignore[arg-type]
            else:
                widget = ChartWidget(title=spec.title, max_points=spec.max_points)
                self.chart_widgets[cid] = widget  # type: ignore[assignment]
                self.bind_map.setdefault(spec.bind, []).append(widget)  # type: ignore[arg-type]
            layout.addWidget(widget)

        for ctrl_id in node.controls:
            spec = self.control_specs.get(ctrl_id)
            if not spec:
                layout.addWidget(QLabel(f"Unknown control: {ctrl_id}"))
                continue
            widget = ControlWidget(spec, self.bus)
            self.control_widgets[ctrl_id] = widget
            layout.addWidget(widget)

        if not node.charts and not node.controls:
            layout.addWidget(QLabel("Empty leaf"))
        return container

    def handle_data(self, payload: Dict[str, float]) -> None:
        """Route incoming data to chart widgets."""
        ts = float(payload.get("ts", 0))
        for key, value in payload.items():
            if key == "ts":
                continue
            widgets = self.bind_map.get(key)
            if not widgets:
                continue
            try:
                val_f = float(value)
            except Exception:
                continue
            for w in widgets:
                w.push_point(ts, val_f)
        for items in self.scatter_specs.values():
            for bx, by, bz, widget in items:
                if bx in payload and by in payload and bz in payload:
                    try:
                        widget.push_point(float(payload[bx]), float(payload[by]), float(payload[bz]))
                    except Exception:
                        continue

    def close_all(self) -> None:
        try:
            self.window.close()
        except Exception:
            pass
        if hasattr(self, "timer") and self.timer.isActive():  # type: ignore[attr-defined]
            self.timer.stop()  # type: ignore[attr-defined]

    def _tick(self) -> None:
        for chart in list(self.chart_widgets.values()):
            if hasattr(chart, "swap_buffers"):
                chart.swap_buffers()
            if hasattr(chart, "update_chart"):
                chart.update_chart()
        for items in self.scatter_specs.values():
            for _, _, _, widget in items:
                if hasattr(widget, "update_chart"):
                    widget.update_chart()
