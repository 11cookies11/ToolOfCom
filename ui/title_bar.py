from __future__ import annotations

try:
    from PySide6.QtCore import QPointF, QSize, Qt
    from PySide6.QtGui import QColor, QGuiApplication, QIcon, QMouseEvent, QPainter, QPen, QPixmap
    from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QPushButton, QWidget
except ImportError:  # pragma: no cover
    from PyQt6.QtCore import QPointF, QSize, Qt  # type: ignore
    from PyQt6.QtGui import QColor, QGuiApplication, QIcon, QMouseEvent, QPainter, QPen, QPixmap  # type: ignore
    from PyQt6.QtWidgets import (  # type: ignore
        QFrame,
        QGraphicsDropShadowEffect,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QWidget,
    )


class TitleButton(QPushButton):
    """自定义标题栏按钮：统一尺寸、矢量图标、悬停高亮。"""

    def __init__(self, kind: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.kind = kind  # min | max | close
        self.state = "max"
        self.setObjectName(f"titleBtn_{kind}")
        self.setCursor(Qt.ArrowCursor)
        self.setFlat(True)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(36, 28)
        self.setIconSize(QSize(18, 18))
        self._base_style = (
            "QPushButton{background: transparent; border: none; border-radius: 6px;}"
            "QPushButton:pressed{background: #0f1626;}"
        )
        self.setStyleSheet(self._base_style)
        self._update_icon(QColor("#1b2333"))

    def enterEvent(self, event) -> None:  # type: ignore[override]
        if self.kind == "close":
            self.setStyleSheet(self._base_style + " QPushButton:hover{background: #f05454;}")
            self._update_icon(QColor("#ffffff"))
        elif self.kind == "min":
            self.setStyleSheet(
                self._base_style + " QPushButton:hover{background: transparent; border-bottom: 2px solid #4AD9FF;}"
            )
            self._update_icon(QColor("#4AD9FF"))
        else:  # max
            self.setStyleSheet(self._base_style + " QPushButton:hover{background: #111b2d;}")
            self._update_icon(QColor("#8B5CFF"))
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self.setStyleSheet(self._base_style)
        self._update_icon(QColor("#1b2333"))
        super().leaveEvent(event)

    def set_restore_mode(self, restore: bool) -> None:
        self.state = "restore" if restore else "max"
        self._update_icon(QColor("#1b2333"))

    def _update_icon(self, color: QColor) -> None:
        size = 18
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(color)
        pen.setWidth(2)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        if self.kind == "min":
            painter.drawLine(3, size // 2 + 3, size - 3, size // 2 + 3)
        elif self.kind == "max":
            if self.state == "restore":
                painter.drawRect(4, 5, size - 10, size - 10)
                painter.drawRect(7, 3, size - 10, size - 10)
            else:
                painter.drawRect(3, 3, size - 6, size - 6)
        else:  # close
            painter.drawLine(4, 4, size - 4, size - 4)
            painter.drawLine(size - 4, 4, 4, size - 4)
        painter.end()
        self.setIcon(QIcon(pm))


class TitleBar(QFrame):
    """自定义标题栏，含拖拽、双击最大化与未来感配色。"""

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.parent = parent
        self.setObjectName("titleBar")
        self.setFixedHeight(36)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        logo = QLabel()
        logo.setObjectName("titleLogo")
        logo.setPixmap(self._build_logo_pixmap())
        logo.setFixedSize(22, 22)

        title = QLabel("ProtoFlow")
        title.setObjectName("titleText")

        layout.addWidget(logo)
        layout.addWidget(title)
        layout.addStretch()

        self.min_btn = TitleButton("min", self)
        self.max_btn = TitleButton("max", self)
        self.close_btn = TitleButton("close", self)

        layout.addWidget(self.min_btn)
        layout.addWidget(self.max_btn)
        layout.addWidget(self.close_btn)

        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(12)
        effect.setColor(QColor(0, 0, 0, 60))
        effect.setOffset(0, 2)
        self.setGraphicsEffect(effect)

        self._dragging = False
        self._drag_pos = None
        self._snap_margin = 16

    def _apply_snap(self, global_pos) -> bool:
        screen = QGuiApplication.screenAt(global_pos)
        if not screen:
            screen = self.parent.screen() if hasattr(self.parent, "screen") else None
        if not screen:
            return False
        rect = screen.availableGeometry()
        x = global_pos.x()
        y = global_pos.y()
        margin = self._snap_margin
        at_left = x <= rect.x() + margin
        at_right = x >= rect.x() + rect.width() - margin
        at_top = y <= rect.y() + margin

        if not (at_left or at_right or at_top):
            return False

        if hasattr(self.parent, "showNormal"):
            self.parent.showNormal()

        if at_top and at_left:
            self.parent.setGeometry(rect.x(), rect.y(), rect.width() // 2, rect.height() // 2)
        elif at_top and at_right:
            self.parent.setGeometry(
                rect.x() + rect.width() // 2,
                rect.y(),
                rect.width() // 2,
                rect.height() // 2,
            )
        elif at_left:
            self.parent.setGeometry(rect.x(), rect.y(), rect.width() // 2, rect.height())
        elif at_right:
            self.parent.setGeometry(rect.x() + rect.width() // 2, rect.y(), rect.width() // 2, rect.height())
        else:
            self.parent.setGeometry(rect)

        if hasattr(self.parent, "title_bar"):
            self.parent.title_bar.set_maximized(False)
        return True

    def _build_logo_pixmap(self) -> QPixmap:
        size = 18
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor("#4AD9FF"))
        pen.setWidth(2)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QColor(74, 217, 255, 24))
        pts = [
            QPointF(size * 0.5, 1),
            QPointF(size - 2, size * 0.28),
            QPointF(size - 2, size * 0.72),
            QPointF(size * 0.5, size - 1),
            QPointF(2, size * 0.72),
            QPointF(2, size * 0.28),
        ]
        painter.drawPolygon(pts)
        painter.drawLine(size * 0.5, 4, size * 0.5, size - 4)
        painter.end()
        return pm

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton and not self._on_controls(event.pos()):
            gp = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
            self._dragging = True
            self._drag_pos = gp - self.parent.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if self._dragging and event.buttons() & Qt.LeftButton and self._drag_pos is not None:
            gp = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
            self.parent.move(gp - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self._drag_pos = None
            gp = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
            if self._apply_snap(gp):
                event.accept()
                return
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if not self._on_controls(event.pos()):
            if hasattr(self.parent, "_toggle_maximize_restore"):
                self.parent._toggle_maximize_restore()
            else:
                self.parent.showMaximized() if not self.parent.isMaximized() else self.parent.showNormal()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def set_maximized(self, maximized: bool) -> None:
        self.max_btn.set_restore_mode(maximized)

    def _on_controls(self, pos) -> bool:
        for btn in (self.min_btn, self.max_btn, self.close_btn):
            if btn.geometry().contains(pos):
                return True
        return False


__all__ = ["TitleBar", "TitleButton"]
