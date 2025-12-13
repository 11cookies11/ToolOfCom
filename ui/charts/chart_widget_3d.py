from __future__ import annotations

from collections import deque
from typing import Deque, Tuple

try:
    from PySide6.QtWidgets import QVBoxLayout, QWidget, QLabel
except ImportError:  # pragma: no cover
    from PyQt6.QtWidgets import QVBoxLayout, QWidget, QLabel  # type: ignore

try:
    import pyqtgraph as pg  # noqa: F401
    import pyqtgraph.opengl as gl
    _has_gl = True
except Exception:  # pragma: no cover
    _has_gl = False
    gl = None  # type: ignore


class Chart3DWidget(QWidget):
    """Simple 3D scatter plot with buffered points."""

    def __init__(self, title: str, max_points: int = 1000) -> None:
        super().__init__()
        self.max_points = max_points
        self.points: Deque[Tuple[float, float, float]] = deque(maxlen=max_points)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        if not _has_gl:
            layout.addWidget(QLabel("3D unavailable (pyqtgraph.opengl missing)"))
            self.view = None
            self.scatter = None
            return

        self.view = gl.GLViewWidget()
        self.view.opts["distance"] = 20
        self.view.setWindowTitle(title)
        grid = gl.GLGridItem()
        grid.scale(1, 1, 1)
        self.view.addItem(grid)

        self.scatter = gl.GLScatterPlotItem()
        self.view.addItem(self.scatter)
        layout.addWidget(self.view)

    def push_point(self, x: float, y: float, z: float) -> None:
        if self.view is None:
            return
        self.points.append((x, y, z))

    def swap_buffers(self) -> None:
        # Not needed; kept for API compatibility
        return

    def update_chart(self) -> None:
        if self.scatter is None or not self.points:
            return
        try:
            import numpy as np
        except Exception:  # pragma: no cover
            pts = [list(p) for p in self.points]
            self.scatter.setData(pos=pts)
            return
        pts = np.array(self.points, dtype=float)
        self.scatter.setData(pos=pts)
