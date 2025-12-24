from __future__ import annotations

from pathlib import Path

try:
    from PySide6.QtCore import QUrl
    from PySide6.QtWidgets import QMainWindow
    from PySide6.QtWebEngineWidgets import QWebEngineView
except ImportError:  # pragma: no cover
    from PyQt6.QtCore import QUrl  # type: ignore
    from PyQt6.QtWidgets import QMainWindow  # type: ignore
    from PyQt6.QtWebEngineWidgets import QWebEngineView  # type: ignore


class WebWindow(QMainWindow):
    """Minimal WebEngine host window for the new web UI."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ProtoFlow Web UI")
        self.resize(1200, 800)

        view = QWebEngineView(self)
        self.setCentralWidget(view)

        index_path = Path(__file__).resolve().parents[1] / "assets" / "web" / "index.html"
        view.load(QUrl.fromLocalFile(str(index_path)))
