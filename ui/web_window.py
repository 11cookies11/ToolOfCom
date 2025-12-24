from __future__ import annotations

from pathlib import Path

try:
    from PySide6.QtCore import Qt, QUrl
    from PySide6.QtWebChannel import QWebChannel
    from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget
    from PySide6.QtWebEngineWidgets import QWebEngineView
except ImportError:  # pragma: no cover
    from PyQt6.QtCore import Qt, QUrl  # type: ignore
    from PyQt6.QtWebChannel import QWebChannel  # type: ignore
    from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget  # type: ignore
    from PyQt6.QtWebEngineWidgets import QWebEngineView  # type: ignore

from ui.web_bridge import WebBridge
from ui.title_bar import TitleBar

class WebWindow(QMainWindow):
    """Minimal WebEngine host window for the new web UI."""

    def __init__(self, bus=None, comm=None) -> None:
        super().__init__()
        self.setWindowTitle("ProtoFlow Web UI")
        self.resize(1200, 800)

        self.setMinimumSize(960, 600)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        self.title_bar = TitleBar(self, title_text=None)
        self.title_bar.min_btn.clicked.connect(self.showMinimized)
        self.title_bar.max_btn.clicked.connect(self._toggle_maximize_restore)
        self.title_bar.close_btn.clicked.connect(self.close)
        self.title_bar.set_maximized(self.isMaximized())

        view = QWebEngineView(self)

        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.title_bar)
        layout.addWidget(view, 1)
        self.setCentralWidget(container)

        channel = QWebChannel(view)
        self.bridge = WebBridge(bus=bus, comm=comm)
        channel.registerObject("bridge", self.bridge)
        view.page().setWebChannel(channel)

        repo_root = Path(__file__).resolve().parents[1]
        dist_index = repo_root / "web-ui" / "dist" / "index.html"
        fallback_index = repo_root / "assets" / "web" / "index.html"
        index_path = dist_index if dist_index.exists() else fallback_index
        view.load(QUrl.fromLocalFile(str(index_path)))

        self._apply_title_style()

    def _toggle_maximize_restore(self) -> None:
        if self.isMaximized():
            self.showNormal()
            self.title_bar.set_maximized(False)
        else:
            self.showMaximized()
            self.title_bar.set_maximized(True)

    def _apply_title_style(self) -> None:
        self.setStyleSheet(
            """
            QFrame#titleBar { background: #f3f3f3; border-bottom: 1px solid #e0e0e0; }
            QLabel#titleText { color: #1e1e1e; font-weight: 600; letter-spacing: 0.2px; }
            QPushButton#titleBtn_min, QPushButton#titleBtn_max, QPushButton#titleBtn_close {
                background: transparent; border: none; color: #1e1e1e;
                border-radius: 6px; padding: 0px; min-height: 28px; min-width: 28px;
            }
            """
        )
