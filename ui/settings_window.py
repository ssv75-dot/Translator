"""Окно настроек приложения."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config.settings import AppSettings, SettingsManager


class SettingsWindow(QDialog):
    """Диалог настроек с вкладками."""

    settings_saved = Signal()

    TRANSLATORS = ["LibreTranslate", "Deep Translator", "OpenAI", "DeepL", "Yandex"]
    OCR_ENGINES = ["Windows OCR", "Tesseract", "PaddleOCR"]
    LANGUAGES = [("Авто", "auto"), ("English", "en"), ("Русский", "ru")]

    def __init__(self, settings_manager: SettingsManager, parent=None) -> None:
        super().__init__(parent)
        self._manager = settings_manager
        self._settings = settings_manager.get()
        self.setWindowTitle("Настройки")
        self.setMinimumSize(480, 520)
        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        tabs.addTab(self._build_general_tab(), "Общие")
        tabs.addTab(self._build_hotkeys_tab(), "Горячие клавиши")
        tabs.addTab(self._build_history_tab(), "История")
        tabs.addTab(self._build_about_tab(), "О программе")
        layout.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet(
            """
            QDialog, QTabWidget, QTabWidget::pane, QWidget {
                background-color: #1e1e2e;
                color: #e8eaf0;
            }
            QTabWidget::pane {
                border: 1px solid #45475a;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #313244;
                color: #e8eaf0;
                padding: 8px 14px;
                margin-right: 2px;
                border: 1px solid #45475a;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #45475a;
                color: #ffffff;
                font-weight: 600;
            }
            QTabBar::tab:!selected:hover {
                background-color: #3b3d52;
                color: #ffffff;
            }
            QLabel {
                color: #e8eaf0;
                background: transparent;
            }
            QCheckBox {
                color: #e8eaf0;
                background: transparent;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #6c7086;
                border-radius: 3px;
                background: #313244;
            }
            QCheckBox::indicator:checked {
                background: #89b4fa;
                border-color: #89b4fa;
            }
            QGroupBox {
                color: #e8eaf0;
                border: 1px solid #45475a;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #181825;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 6px;
                color: #e8eaf0;
                background-color: #1e1e2e;
            }
            QLineEdit, QComboBox, QListWidget {
                background-color: #313244;
                color: #ffffff;
                border: 1px solid #585b70;
                border-radius: 4px;
                padding: 4px;
                selection-background-color: #89b4fa;
                selection-color: #1e1e2e;
            }
            QComboBox QAbstractItemView {
                background-color: #313244;
                color: #ffffff;
                selection-background-color: #45475a;
                selection-color: #ffffff;
            }
            QPushButton, QDialogButtonBox QPushButton {
                background-color: #313244;
                color: #ffffff;
                border: 1px solid #585b70;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover, QDialogButtonBox QPushButton:hover {
                background-color: #45475a;
            }
            QListWidget::item {
                color: #e8eaf0;
                padding: 4px;
            }
            QListWidget::item:selected {
                background-color: #45475a;
                color: #ffffff;
            }
            """
        )

    def _build_general_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self._translator_combo = QComboBox()
        self._translator_combo.addItems(self.TRANSLATORS)
        form.addRow("Переводчик:", self._translator_combo)

        self._source_combo = QComboBox()
        self._target_combo = QComboBox()
        for label, code in self.LANGUAGES:
            self._source_combo.addItem(label, code)
        for label, code in self.LANGUAGES:
            if code != "auto":
                self._target_combo.addItem(label, code)
        form.addRow("Источник:", self._source_combo)
        form.addRow("Получатель:", self._target_combo)

        self._ocr_combo = QComboBox()
        self._ocr_combo.addItems(self.OCR_ENGINES)
        form.addRow("OCR:", self._ocr_combo)

        api_group = QGroupBox("API-ключи (при необходимости)")
        api_form = QFormLayout(api_group)
        self._openai_key = QLineEdit()
        self._openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._deepl_key = QLineEdit()
        self._deepl_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._yandex_key = QLineEdit()
        self._yandex_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._libre_url = QLineEdit()
        api_form.addRow("OpenAI:", self._openai_key)
        api_form.addRow("DeepL:", self._deepl_key)
        api_form.addRow("Yandex:", self._yandex_key)
        api_form.addRow("LibreTranslate URL:", self._libre_url)
        form.addRow(api_group)

        self._autostart_cb = QCheckBox("Запуск вместе с Windows")
        self._tray_cb = QCheckBox("Сворачивать в трей")
        self._ontop_cb = QCheckBox("Поверх всех окон")
        self._copy_cb = QCheckBox("Копировать перевод автоматически")
        form.addRow(self._autostart_cb)
        form.addRow(self._tray_cb)
        form.addRow(self._ontop_cb)
        form.addRow(self._copy_cb)
        return widget

    def _build_hotkeys_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        self._hotkey_translate = QLineEdit()
        self._hotkey_capture = QLineEdit()
        self._hotkey_translate.setPlaceholderText("Ctrl+Shift+T")
        self._hotkey_capture.setPlaceholderText("Ctrl+Shift+S")
        form.addRow("Перевести текст:", self._hotkey_translate)
        form.addRow("Сделать снимок:", self._hotkey_capture)
        hint = QLabel("Формат: Ctrl+Shift+T, Alt+Q и т.д.")
        hint.setWordWrap(True)
        form.addRow(hint)
        return widget

    def _build_history_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self._history_list = QListWidget()
        layout.addWidget(self._history_list)
        clear_btn = QPushButton("Очистить историю")
        clear_btn.clicked.connect(self._clear_history)
        layout.addWidget(clear_btn)
        return widget


    def _build_about_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addStretch()
        title = QLabel("Screen Translator")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #89b4fa; background: transparent;")
        author = QLabel("Created by Sergey Stefanchishen")
        author.setAlignment(Qt.AlignmentFlag.AlignCenter)
        author.setStyleSheet("font-size: 13px; color: #e8eaf0; background: transparent;")
        layout.addWidget(title)
        layout.addWidget(author)
        layout.addStretch()
        return widget

    def _load_values(self) -> None:
        s = self._settings
        idx = self._translator_combo.findText(s.translator)
        if idx >= 0:
            self._translator_combo.setCurrentIndex(idx)
        idx = self._ocr_combo.findText(s.ocr)
        if idx >= 0:
            self._ocr_combo.setCurrentIndex(idx)
        for combo, value in ((self._source_combo, s.source_language), (self._target_combo, s.target_language)):
            for i in range(combo.count()):
                if combo.itemData(i) == value:
                    combo.setCurrentIndex(i)
                    break
        self._openai_key.setText(s.openai_api_key)
        self._deepl_key.setText(s.deepl_api_key)
        self._yandex_key.setText(s.yandex_api_key)
        self._libre_url.setText(s.libretranslate_url)
        self._autostart_cb.setChecked(s.start_with_windows)
        self._tray_cb.setChecked(s.minimize_to_tray)
        self._ontop_cb.setChecked(s.always_on_top)
        self._copy_cb.setChecked(s.copy_result)
        self._hotkey_translate.setText(s.hotkey_translate)
        self._hotkey_capture.setText(s.hotkey_capture)
        self._refresh_history()

    def _refresh_history(self) -> None:
        self._history_list.clear()
        for entry in self._manager.get_history():
            self._history_list.addItem(
                f"{entry['date']}\n{entry['source_text'][:60]} → {entry['translated_text'][:60]}"
            )

    def _clear_history(self) -> None:
        reply = QMessageBox.question(
            self, "Очистить историю", "Удалить все записи истории?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._manager.clear_history()
            self._refresh_history()

    def _save(self) -> None:
        try:
            self._manager.update(
                translator=self._translator_combo.currentText(),
                ocr=self._ocr_combo.currentText(),
                source_language=self._source_combo.currentData(),
                target_language=self._target_combo.currentData(),
                openai_api_key=self._openai_key.text().strip(),
                deepl_api_key=self._deepl_key.text().strip(),
                yandex_api_key=self._yandex_key.text().strip(),
                libretranslate_url=self._libre_url.text().strip() or "https://libretranslate.com",
                start_with_windows=self._autostart_cb.isChecked(),
                minimize_to_tray=self._tray_cb.isChecked(),
                always_on_top=self._ontop_cb.isChecked(),
                copy_result=self._copy_cb.isChecked(),
                hotkey_translate=self._hotkey_translate.text().strip() or "Ctrl+Shift+T",
                hotkey_capture=self._hotkey_capture.text().strip() or "Ctrl+Shift+S",
            )
            self._manager.apply_autostart(self._autostart_cb.isChecked())
        except Exception as error:
            QMessageBox.critical(self, "Ошибка", str(error))
            return
        self.settings_saved.emit()
        self.accept()