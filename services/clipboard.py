"""Работа с буфером обмена и имитация Ctrl+C."""

from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

import keyboard
import pyperclip

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class ClipboardService:
    """Получение и установка текста через буфер обмена Windows."""

    def __init__(self, copy_delay: float = 0.3) -> None:
        self._copy_delay = copy_delay
        self._own_hwnds: set[int] = set()
        self._last_foreign_hwnd: int | None = None

    def register_own_hwnd(self, hwnd: int) -> None:
        self._own_hwnds.add(int(hwnd))

    def track_foreground_window(self) -> None:
        hwnd = int(user32.GetForegroundWindow())
        if hwnd and hwnd not in self._own_hwnds:
            self._last_foreign_hwnd = hwnd

    def _restore_foreign_focus(self) -> None:
        if not self._last_foreign_hwnd:
            return
        try:
            if user32.IsWindow(self._last_foreign_hwnd):
                user32.SetForegroundWindow(self._last_foreign_hwnd)
                time.sleep(0.08)
        except Exception:
            pass

    def simulate_copy(self) -> None:
        self._restore_foreign_focus()
        keyboard.send("ctrl+c")
        time.sleep(self._copy_delay)

    def get_text(self) -> str:
        try:
            text = pyperclip.paste()
        except pyperclip.PyperclipException as error:
            raise ClipboardError("Не удалось прочитать буфер обмена.") from error
        return (text or "").strip()

    def set_text(self, text: str) -> None:
        try:
            pyperclip.copy(text)
        except pyperclip.PyperclipException as error:
            raise ClipboardError("Не удалось записать в буфер обмена.") from error

    def capture_selected_text(self) -> str:
        self.track_foreground_window()
        previous = self.get_text()
        for _ in range(3):
            self.simulate_copy()
            captured = self.get_text()
            if captured and captured != previous:
                return captured
            if captured and not previous:
                return captured
            time.sleep(0.1)
        return self.get_text()


class ClipboardError(Exception):
    """Ошибка при работе с буфером обмена."""