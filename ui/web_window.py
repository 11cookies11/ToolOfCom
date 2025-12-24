from __future__ import annotations

from pathlib import Path

try:
    from PySide6.QtCore import QPoint, Qt, QUrl
    from PySide6.QtGui import QAction, QGuiApplication
    from PySide6.QtWebChannel import QWebChannel
    from PySide6.QtWidgets import QMainWindow, QMenu
    from PySide6.QtWebEngineWidgets import QWebEngineView
except ImportError:  # pragma: no cover
    from PyQt6.QtCore import QPoint, Qt, QUrl  # type: ignore
    from PyQt6.QtGui import QAction, QGuiApplication  # type: ignore
    from PyQt6.QtWebChannel import QWebChannel  # type: ignore
    from PyQt6.QtWidgets import QMainWindow, QMenu  # type: ignore
    from PyQt6.QtWebEngineWidgets import QWebEngineView  # type: ignore

from ui.web_bridge import WebBridge

class WebWindow(QMainWindow):
    """Minimal WebEngine host window for the new web UI."""

    def __init__(self, bus=None, comm=None) -> None:
        super().__init__()
        self.setWindowTitle("ProtoFlow Web UI")
        self.resize(1200, 800)
        self._normal_geometry = self.geometry()
        self._titlebar_height = 30

        self.setMinimumSize(960, 600)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        view = QWebEngineView(self)
        self.setCentralWidget(view)

        channel = QWebChannel(view)
        self.bridge = WebBridge(bus=bus, comm=comm, window=self)
        channel.registerObject("bridge", self.bridge)
        view.page().setWebChannel(channel)

        repo_root = Path(__file__).resolve().parents[1]
        dist_index = repo_root / "web-ui" / "dist" / "index.html"
        fallback_index = repo_root / "assets" / "web" / "index.html"
        index_path = dist_index if dist_index.exists() else fallback_index
        view.load(QUrl.fromLocalFile(str(index_path)))

    def _apply_snap(self, screen_x: int, screen_y: int) -> bool:
        screen = QGuiApplication.screenAt(QPoint(screen_x, screen_y))
        if not screen:
            screen = self.screen() if hasattr(self, "screen") else None
        if not screen:
            return False
        rect = screen.availableGeometry()
        margin = 16
        at_left = screen_x <= rect.x() + margin
        at_right = screen_x >= rect.x() + rect.width() - margin
        at_top = screen_y <= rect.y() + margin
        if not (at_left or at_right or at_top):
            return False
        self.showNormal()
        if at_top and not (at_left or at_right):
            self._remember_normal_geometry()
            self.showMaximized()
            return True
        if at_top and at_left:
            self.setGeometry(rect.x(), rect.y(), rect.width() // 2, rect.height() // 2)
        elif at_top and at_right:
            self.setGeometry(
                rect.x() + rect.width() // 2,
                rect.y(),
                rect.width() // 2,
                rect.height() // 2,
            )
        elif at_left:
            self.setGeometry(rect.x(), rect.y(), rect.width() // 2, rect.height())
        elif at_right:
            self.setGeometry(rect.x() + rect.width() // 2, rect.y(), rect.width() // 2, rect.height())
        else:
            self._remember_normal_geometry()
            self.setGeometry(rect)
        return True

    def _start_move(self, screen_x: int, screen_y: int) -> None:
        handle = self.windowHandle()
        if self.isMaximized():
            screen = QGuiApplication.screenAt(QPoint(screen_x, screen_y))
            if not screen:
                screen = self.screen() if hasattr(self, "screen") else None
            normal = self._get_normal_geometry()
            self.showNormal()
            self.setWindowState(self.windowState() & ~Qt.WindowMaximized)
            self.setGeometry(self.x(), self.y(), normal.width(), normal.height())
        if handle and hasattr(handle, "startSystemMove"):
            handle.startSystemMove()

    def _show_system_menu(self, screen_x: int, screen_y: int) -> None:
        menu = QMenu(self)
        action_restore = QAction("Restore", self)
        action_move = QAction("Move", self)
        action_size = QAction("Size", self)
        action_min = QAction("Minimize", self)
        action_max = QAction("Maximize", self)
        action_close = QAction("Close", self)

        action_restore.setEnabled(self.isMaximized() or self.isMinimized())
        action_max.setEnabled(not self.isMaximized())
        action_min.setEnabled(not self.isMinimized())

        action_restore.triggered.connect(self.showNormal)
        action_min.triggered.connect(self.showMinimized)
        action_max.triggered.connect(self.showMaximized)
        action_close.triggered.connect(self.close)

        def _move_window() -> None:
            handle = self.windowHandle()
            if handle and hasattr(handle, "startSystemMove"):
                handle.startSystemMove()

        def _resize_window() -> None:
            handle = self.windowHandle()
            if handle and hasattr(handle, "startSystemResize"):
                handle.startSystemResize(Qt.BottomEdge | Qt.RightEdge)

        action_move.triggered.connect(_move_window)
        action_size.triggered.connect(_resize_window)

        menu.addAction(action_restore)
        menu.addSeparator()
        menu.addAction(action_move)
        menu.addAction(action_size)
        menu.addSeparator()
        menu.addAction(action_min)
        menu.addAction(action_max)
        menu.addSeparator()
        menu.addAction(action_close)

        menu.exec(QPoint(screen_x, screen_y))

    def _start_resize(self, edge: str) -> None:
        handle = self.windowHandle()
        if not handle or not hasattr(handle, "startSystemResize"):
            return
        edge_map = {
            "left": Qt.LeftEdge,
            "right": Qt.RightEdge,
            "top": Qt.TopEdge,
            "bottom": Qt.BottomEdge,
            "top-left": Qt.TopEdge | Qt.LeftEdge,
            "top-right": Qt.TopEdge | Qt.RightEdge,
            "bottom-left": Qt.BottomEdge | Qt.LeftEdge,
            "bottom-right": Qt.BottomEdge | Qt.RightEdge,
        }
        qt_edge = edge_map.get(edge)
        if qt_edge is None:
            return
        handle.startSystemResize(qt_edge)

    def _update_normal_geometry(self) -> None:
        if not self.isMaximized() and not self.isMinimized():
            self._normal_geometry = self.geometry()

    def _remember_normal_geometry(self) -> None:
        if not self.isMaximized() and not self.isMinimized():
            self._normal_geometry = self.geometry()

    def _get_normal_geometry(self):
        normal = self._normal_geometry
        if normal is None:
            normal = self.normalGeometry()
        return normal

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_normal_geometry()

    def moveEvent(self, event) -> None:  # type: ignore[override]
        super().moveEvent(event)
        self._update_normal_geometry()
