"""Оверлей выбора области поверх снимка рабочего стола."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from services.screenshot import ScreenRegion


class ScreenshotOverlay(QWidget):
    region_selected = Signal(object)
    selection_cancelled = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._origin = QPoint()
        self._current = QPoint()
        self._selecting = False
        self._background: QPixmap | None = None
        self._desktop_offset = QPoint(0, 0)
        self._setup_window()

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setCursor(Qt.CursorShape.CrossCursor)

    def prepare(self, background: QPixmap, left: int, top: int, width: int, height: int) -> None:
        """Показывает замороженный снимок экрана вместо чёрного оверлея."""
        self._background = background
        self._desktop_offset = QPoint(left, top)
        self._origin = QPoint()
        self._current = QPoint()
        self._selecting = False
        self.setGeometry(left, top, width, height)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        if self._background and not self._background.isNull():
            painter.drawPixmap(self.rect(), self._background)
        else:
            painter.fillRect(self.rect(), QColor(30, 30, 46))

        painter.fillRect(self.rect(), QColor(0, 0, 0, 90))

        if self._selecting:
            rect = QRect(self._origin, self._current).normalized()
            if self._background and not self._background.isNull():
                painter.drawPixmap(rect, self._background, rect)
            painter.setPen(QPen(QColor(137, 180, 250), 2, Qt.PenStyle.SolidLine))
            painter.drawRect(rect)

        painter.setPen(QColor(205, 214, 244))
        painter.setFont(QFont("Segoe UI", 11))
        painter.drawText(
            16,
            28,
            "Выделите область мышью. Esc — отмена",
        )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.position().toPoint()
            self._current = self._origin
            self._selecting = True
            self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._selecting:
            self._current = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._selecting:
            self._selecting = False
            rect = QRect(self._origin, self._current).normalized()
            self.hide()
            if rect.width() > 2 and rect.height() > 2:
                region = ScreenRegion(
                    self._desktop_offset.x() + rect.left(),
                    self._desktop_offset.y() + rect.top(),
                    rect.width(),
                    rect.height(),
                )
                self.region_selected.emit(region)
            else:
                self.selection_cancelled.emit()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            self.selection_cancelled.emit()