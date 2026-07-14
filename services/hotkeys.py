"""Глобальные горячие клавиши (вызовы передаются через Qt Signal в GUI-поток)."""

from __future__ import annotations

from typing import Callable

import keyboard


class HotkeyService:
    """Регистрация системных горячих клавиш."""

    def __init__(self) -> None:
        self._registered: list[tuple[str, Callable[[], None]]] = []

    def register(self, hotkey: str, callback: Callable[[], None]) -> None:
        """Регистрирует горячую клавишу. callback должен быть thread-safe (например, Signal.emit)."""
        normalized = self._normalize(hotkey)
        keyboard.add_hotkey(normalized, callback, suppress=False)
        self._registered.append((normalized, callback))

    def unregister_all(self) -> None:
        for hotkey, _callback in self._registered:
            try:
                keyboard.remove_hotkey(hotkey)
            except KeyError:
                pass
        self._registered.clear()

    def reload(self, bindings: dict[str, Callable[[], None]]) -> None:
        self.unregister_all()
        for hotkey, callback in bindings.items():
            self.register(hotkey, callback)

    @staticmethod
    def _normalize(hotkey: str) -> str:
        return hotkey.replace(" ", "").lower()


class HotkeyError(Exception):
    """Ошибка регистрации горячих клавиш."""