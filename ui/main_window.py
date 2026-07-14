"""Главное окно приложения Screen Translator."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    """Компактное главное окно со статусом и кнопками управления."""

    translate_requested = Signal()
    capture_requested = Signal()
    settings_requested = Signal()
    quit_requested = Signal()

    def __init__(self, tray_icon: QIcon | None = None) -> None:
        super().__init__()
        self._minimize_to_tray = True
        self._tray_icon = None
        self._status_label: QLabel | None = None
        self._build_ui()
        if tray_icon is not None:
            self._setup_tray(tray_icon)

    def _build_ui(self) -> None:
        self.setWindowTitle("Screen Translator")
        self.setFixedSize(320, 220)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setSpacing(12)

        status_row = QHBoxLayout()
        dot = QLabel("●")
        dot.setStyleSheet("color: #a6e3a1; font-size: 16px;")
        self._status_label = QLabel("Запущено")
        status_row.addWidget(dot)
        status_row.addWidget(self._status_label)
        status_row.addStretch()
        layout.addLayout(status_row)

        btn_translate = QPushButton("Перевести выделенный текст")
        btn_translate.clicked.connect(self.translate_requested.emit)
        layout.addWidget(btn_translate)

        btn_capture = QPushButton("Сделать снимок")
        btn_capture.clicked.connect(self.capture_requested.emit)
        layout.addWidget(btn_capture)

        row = QHBoxLayout()
        btn_settings = QPushButton("Настройки")
        btn_settings.clicked.connect(self.settings_requested.emit)
        btn_exit = QPushButton("Выход")
        btn_exit.clicked.connect(self.quit_requested.emit)
        row.addWidget(btn_settings)
        row.addWidget(btn_exit)
        layout.addLayout(row)

        self.setCentralWidget(central)
        self.setStyleSheet(
            """
            QMainWindow { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; }
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #45475a; }
            """
        )

    def _setup_tray(self, icon: QIcon) -> None:
        self._tray_icon = QSystemTrayIcon(icon, self)
        menu = self._tray_icon.contextMenu()
        if menu is None:
            from PySide6.QtWidgets import QMenu

            menu = QMenu(self)
            open_action = QAction("Открыть", self)
            open_action.triggered.connect(self.show_main_window)
            settings_action = QAction("Настройки", self)
            settings_action.triggered.connect(self.settings_requested.emit)
            quit_action = QAction("Выход", self)
            quit_action.triggered.connect(self.quit_requested.emit)
            menu.addAction(open_action)
            menu.addAction(settings_action)
            menu.addSeparator()
            menu.addAction(quit_action)
            self._tray_icon.setContextMenu(menu)
        self._tray_icon.setToolTip("Screen Translator")
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_main_window()

    def show_main_window(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def set_minimize_to_tray(self, enabled: bool) -> None:
        self._minimize_to_tray = enabled

    def show_message(self, title: str, text: str) -> None:
        QMessageBox.warning(self, title, text)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._minimize_to_tray and self._tray_icon is not None:
            event.ignore()
            self.hide()
            self._tray_icon.showMessage(
                "Screen Translator",
                "Приложение свёрнуто в трей.",
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )
        else:
            super().closeEvent(event)