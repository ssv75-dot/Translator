"""
Screen Translator — точка входа приложения.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

if getattr(sys, "frozen", False):
    sys.path.insert(0, sys._MEIPASS)
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
    QSplashScreen,
    QStyle,
    QSystemTrayIcon,
)

from config.settings import SettingsManager
from services.clipboard import ClipboardService
from services.hotkeys import HotkeyService
from services.logger import AppLogger
from services.translator import NetworkError, TranslationError
from ui.main_window import MainWindow
from ui.popup_window import PopupWindow
from ui.screenshot_overlay import ScreenshotOverlay
from ui.settings_window import SettingsWindow


class ApplicationController(QObject):
    """Связывает UI, сервисы и обработку горячих клавиш."""

    hotkey_translate = Signal()
    hotkey_capture = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._settings_manager = SettingsManager()
        self._logger = AppLogger(self._settings_manager.base_dir / "logs")
        self._clipboard = ClipboardService()
        self._hotkeys = HotkeyService()
        # Heavy OCR / screenshot / translator stack is created after UI is shown.
        self._screenshot = None
        self._ocr = None
        self._translator = None
        self._services_ready = False
        self._popup = PopupWindow(self._settings_manager.get().always_on_top)
        self._overlay: ScreenshotOverlay | None = None
        self._main_window = MainWindow(self._create_tray_icon())
        self._settings_window: SettingsWindow | None = None
        self._connect_signals()
        self._apply_settings()
        self._clipboard.register_own_hwnd(int(self._main_window.winId()))
        self._focus_timer = QTimer(self)
        self._focus_timer.timeout.connect(self._clipboard.track_foreground_window)
        self._focus_timer.start(300)

    def _create_tray_icon(self) -> QIcon:
        icon_path = self._settings_manager.base_dir / "resources" / "icon.png"
        if icon_path.exists():
            return QIcon(str(icon_path))
        return QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)

    def _connect_signals(self) -> None:
        self._main_window.translate_requested.connect(self.translate_selection)
        self._main_window.capture_requested.connect(self.start_capture)
        self._main_window.settings_requested.connect(self.open_settings)
        self._main_window.quit_requested.connect(self.quit_application)
        self.hotkey_translate.connect(self.translate_selection)
        self.hotkey_capture.connect(self.start_capture)

    def _ensure_overlay(self) -> ScreenshotOverlay:
        if self._overlay is None:
            self._overlay = ScreenshotOverlay()
            self._overlay.region_selected.connect(self._on_region_selected)
            self._overlay.selection_cancelled.connect(self._on_capture_cancelled)
        return self._overlay

    def deferred_init(self) -> None:
        # Register hotkeys quickly; OCR/translator load on first use.
        QApplication.processEvents()
        self._apply_settings()
        self._register_hotkeys()

    def _ensure_services(self) -> None:
        """Lazy-load OCR / screenshot / translator so UI appears sooner."""
        if self._services_ready:
            return
        from services.ocr import OcrService
        from services.screenshot import ScreenshotService
        from services.translator import TranslatorService

        settings = self._settings_manager.get()
        self._screenshot = ScreenshotService()
        self._ocr = OcrService(settings.ocr, self._logger, self._settings_manager.base_dir)
        self._translator = TranslatorService(settings, self._logger)
        self._services_ready = True

    def _apply_settings(self) -> None:
        settings = self._settings_manager.get()
        self._main_window.set_minimize_to_tray(settings.minimize_to_tray)
        self._popup.set_always_on_top(settings.always_on_top)
        if self._services_ready and self._ocr is not None and self._translator is not None:
            self._ocr.set_engine(settings.ocr)
            self._translator.update_settings(settings)

    def _register_hotkeys(self) -> None:
        settings = self._settings_manager.get()
        self._hotkeys.reload({
            settings.hotkey_translate: self.hotkey_translate.emit,
            settings.hotkey_capture: self.hotkey_capture.emit,
        })

    def show(self) -> None:
        settings = self._settings_manager.get()
        if settings.minimize_to_tray:
            self._main_window.hide()
        else:
            self._main_window.show()

    @Slot()
    def translate_selection(self) -> None:
        try:
            self._ensure_services()
            self._main_window.hide()
            QApplication.processEvents()
            time.sleep(0.12)
            text = self._clipboard.capture_selected_text()
            if not text:
                self._show_error(
                    "Текст не найден.\n\n"
                    "1. Выделите текст в другом приложении.\n"
                    "2. Нажмите Ctrl+Shift+T (рекомендуется).\n"
                    "3. Или нажмите кнопку, не снимая выделения."
                )
                return
            self._translate_and_show(text)
        except Exception as error:
            self._show_error(str(error))

    def _ensure_ocr_ready(self) -> bool:
        from services.ocr import OcrService

        status = OcrService.check_availability(
            self._settings_manager.get().ocr,
            self._settings_manager.base_dir,
        )
        messages = status.get("messages", [])
        if messages:
            self._show_error(messages[0])
            return False
        return True

    @Slot()
    def start_capture(self) -> None:
        self._ensure_services()
        if not self._ensure_ocr_ready():
            return
        self._main_window.hide()
        QApplication.processEvents()
        QTimer.singleShot(150, self._show_capture_overlay)

    def _pil_to_pixmap(self, image) -> QPixmap:
        data = image.tobytes("raw", "RGB")
        qimg = QImage(
            data,
            image.width,
            image.height,
            image.width * 3,
            QImage.Format.Format_RGB888,
        )
        return QPixmap.fromImage(qimg.copy())

    def _show_capture_overlay(self) -> None:
        from services.screenshot import ScreenshotError

        try:
            self._ensure_services()
            desktop = self._screenshot.capture_desktop()
            overlay = self._ensure_overlay()
            overlay.prepare(
                self._pil_to_pixmap(desktop.image),
                desktop.left,
                desktop.top,
                desktop.width,
                desktop.height,
            )
            overlay.show()
            overlay.raise_()
            overlay.activateWindow()
        except ScreenshotError as error:
            self._show_error(str(error))
            self._restore_main_window()

    def _on_region_selected(self, region) -> None:
        from services.ocr import OcrError

        try:
            self._ensure_services()
            image = self._screenshot.capture_region(region)
            text = self._ocr.recognize(image)
            self._translate_and_show(text)
        except OcrError as error:
            self._logger.log_ocr_error(str(error))
            self._show_error(str(error))
        except Exception as error:
            self._show_error(str(error))
        finally:
            self._restore_main_window()

    def _on_capture_cancelled(self) -> None:
        self._restore_main_window()

    def _restore_main_window(self) -> None:
        if not self._settings_manager.get().minimize_to_tray:
            self._main_window.show_main_window()

    def _translate_and_show(self, text: str) -> None:
        self._ensure_services()
        settings = self._settings_manager.get()
        try:
            result = self._translator.translate(text)
            self._settings_manager.add_history_entry(result.original, result.translated)
            if settings.copy_result:
                self._clipboard.set_text(result.translated)
            self._popup.show_translation(result.original, result.translated)
        except NetworkError as error:
            self._logger.log_network_error(str(error))
            self._show_error("Нет подключения к Интернету.")
        except TranslationError as error:
            self._logger.log_translation_error(str(error))
            self._show_error(str(error))
        except Exception as error:
            self._logger.log_translation_error("Неизвестная ошибка", error)
            self._show_error("Не удалось выполнить перевод.")

    def _show_error(self, message: str) -> None:
        QMessageBox.warning(self._main_window, "Screen Translator", message)

    @Slot()
    def open_settings(self) -> None:
        self._settings_window = SettingsWindow(self._settings_manager, self._main_window)
        self._settings_window.settings_saved.connect(self._on_settings_saved)
        self._settings_window.exec()

    def _on_settings_saved(self) -> None:
        self._apply_settings()
        QTimer.singleShot(0, self._register_hotkeys)

    def quit_application(self) -> None:
        self._hotkeys.unregister_all()
        QApplication.instance().quit()


def configure_high_dpi() -> None:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )


def main() -> int:
    configure_high_dpi()
    app = QApplication(sys.argv)
    app.setApplicationName("Screen Translator")
    app.setQuitOnLastWindowClosed(False)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "Screen Translator", "Системный трей недоступен.")
        return 1

    splash = QSplashScreen(QPixmap())
    splash.showMessage(
        "Загрузка Screen Translator...",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
        Qt.GlobalColor.white,
    )
    splash.show()
    app.processEvents()

    controller = ApplicationController()
    controller.show()
    splash.finish(controller._main_window)
    QTimer.singleShot(0, controller.deferred_init)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())