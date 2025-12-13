from __future__ import annotations

import time
from typing import Dict, Iterable, List

from PySide6.QtCore import QObject

from dsl.ast_nodes import ChartSpec
from ui.charts.chart_widget import ChartWidget
from ui.charts.chart_widget_3d import Chart3DWidget
from ui.charts.script_window import ScriptWindow


class WindowManager(QObject):
    """Create script windows from chart specs and route data by bind key."""

    def __init__(self, chart_specs: Iterable[ChartSpec], parent=None) -> None:
        super().__init__(parent)
        self.chart_specs = list(chart_specs)
        self.windows: List[ScriptWindow] = []
        self.bind_map: Dict[str, List[ChartWidget]] = {}
        self._build()

    def _build(self) -> None:
        grouped: Dict[str, List[ChartWidget]] = {}
        separate: List[tuple[ChartSpec, ChartWidget]] = []
        self.scatter_specs: List[tuple[str, str, str, Chart3DWidget]] = []

        for spec in self.chart_specs:
            chart = self._make_chart(spec)
            if spec.separate:
                separate.append((spec, chart))
            else:
                group_name = spec.group or "default"
                grouped.setdefault(group_name, []).append(chart)

        for group_name, charts in grouped.items():
            title = f"Charts: {group_name}"
            win = ScriptWindow(title=title, charts=charts)
            self.windows.append(win)
            win.show()

        for spec, chart in separate:
            win = ScriptWindow(title=spec.title, charts=[chart])
            self.windows.append(win)
            win.show()

    def _make_chart(self, spec: ChartSpec) -> ChartWidget:
        if spec.chart_type == "scatter3d":
            widget = Chart3DWidget(title=spec.title, max_points=spec.max_points)
            if spec.bind_x and spec.bind_y and spec.bind_z:
                self.scatter_specs.append((spec.bind_x, spec.bind_y, spec.bind_z, widget))
            return widget  # type: ignore[return-value]
        chart = ChartWidget(title=spec.title, max_points=spec.max_points)
        self.bind_map.setdefault(spec.bind, []).append(chart)
        return chart

    def handle_data(self, payload: Dict[str, float]) -> None:
        """Route incoming parsed data dict to bound charts."""
        ts = float(payload.get("ts", time.time()))
        # 2D
        for key, value in payload.items():
            if key == "ts":
                continue
            charts = self.bind_map.get(key)
            if charts:
                try:
                    val_f = float(value)
                except Exception:
                    continue
                for chart in charts:
                    chart.push_point(ts, val_f)
        # 3D
        for bx, by, bz, widget in self.scatter_specs:
            if bx in payload and by in payload and bz in payload:
                try:
                    widget.push_point(float(payload[bx]), float(payload[by]), float(payload[bz]))
                except Exception:
                    continue

    def close_all(self) -> None:
        for win in self.windows:
            win.close()
