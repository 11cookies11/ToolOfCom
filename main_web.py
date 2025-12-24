"""WebEngine UI entrypoint."""

from __future__ import annotations

import sys

try:
    from PySide6.QtWidgets import QApplication
except ImportError:  # pragma: no cover
    from PyQt6.QtWidgets import QApplication  # type: ignore

from ui.web_window import WebWindow


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    window = WebWindow()
    window.show()
    print("ProtoFlow Web UI started")
    app.exec()


if __name__ == "__main__":
    main()
