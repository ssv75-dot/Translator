"""Окно отображения перевода поверх всех окон."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class PopupWindow(QWidget):
    """Безрамочное окно с оригиналом и переводом."""

    closed = Signal()

    def __init__(self, always_on_top: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._always_on_top = always_on_top
        self._drag_position = None
        self._build_ui()
        self._setup_shortcuts()
        self.hide()

    def _build_ui(self) -> None:
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self._always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumWidth(360)
        self.setMaximumWidth(520)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        self.setStyleSheet(
            """
            QWidget#popupRoot {
                background-color: #1e1e2e;
                border: 1px solid #45475a;
                border-radius: 10px;
            }
            QLabel { color: #cdd6f4; }
            QLabel#sectionTitle { color: #89b4fa; font-weight: bold; }
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 6px 14px;
            }
            QPushButton:hover { background-color: #45475a; }
            """
        )
        self.setObjectName("popupRoot")

        separator = lambda: self._make_separator()

        root.addWidget(self._section_title("Original"))
        self._original_label = QLabel()
        self._original_label.setWordWrap(True)
        self._original_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(self._original_label)
        root.addWidget(separator())
        root.addWidget(self._section_title("Перевод"))
        self._translated_label = QLabel()
        self._translated_label.setWordWrap(True)
        self._translated_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        font = QFont()
        font.setPointSize(11)
        self._translated_label.setFont(font)
        root.addWidget(self._translated_label)
        root.addWidget(separator())

        buttons = QHBoxLayout()
        buttons.addStretch()
        copy_btn = QPushButton("Копировать")
        copy_btn.clicked.connect(self._on_copy)
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.close)
        buttons.addWidget(copy_btn)
        buttons.addWidget(close_btn)
        root.addLayout(buttons)

        self._translated_text = ""

    def _section_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        return label

    @staticmethod
    def _make_separator() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #45475a;")
        return line

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, activated=self.close)


    def _is_draggable_target(self, pos) -> bool:
        child = self.childAt(pos)
        return not isinstance(child, QPushButton)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._is_draggable_target(event.position().toPoint()):
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_position is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_position = None
        super().mouseReleaseEvent(event)

    def show_translation(self, original: str, translated: str) -> None:
        self._original_label.setText(original)
        self._translated_label.setText(translated)
        self._translated_text = translated
        self.adjustSize()
        self.show()
        self.raise_()
        self.activateWindow()

    def set_always_on_top(self, enabled: bool) -> None:
        self._always_on_top = enabled
        was_visible = self.isVisible()
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if enabled:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        # setWindowFlags скрывает окно — восстанавливаем только если оно уже было открыто
        if was_visible:
            self.show()

    def _on_copy(self) -> None:
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(self._translated_text)

    def closeEvent(self, event) -> None:
        self.closed.emit()
        super().closeEvent(event)