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
            self.setGeometry(rect)
        return True

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
