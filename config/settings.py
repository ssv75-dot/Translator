"""Модуль управления настройками приложения Screen Translator."""

from __future__ import annotations

import json
import logging
import sys
import winreg
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

MAX_HISTORY_SIZE = 100
APP_NAME = "ScreenTranslator"


@dataclass
class HistoryEntry:
    """Одна запись в истории переводов."""

    date: str
    source_text: str
    translated_text: str


@dataclass
class AppSettings:
    """Структура настроек приложения."""

    translator: str = "Deep Translator"
    ocr: str = "Windows OCR"
    source_language: str = "auto"
    target_language: str = "ru"
    copy_result: bool = False
    always_on_top: bool = True
    minimize_to_tray: bool = True
    start_with_windows: bool = False
    hotkey_translate: str = "Ctrl+Shift+T"
    hotkey_capture: str = "Ctrl+Shift+S"
    openai_api_key: str = ""
    deepl_api_key: str = ""
    yandex_api_key: str = ""
    libretranslate_url: str = "https://libretranslate.com"
    history: list[dict[str, str]] = field(default_factory=list)


class SettingsManager:
    """Менеджер настроек: чтение, запись, история, автозапуск."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or self._detect_base_dir()
        self._settings_path = self._base_dir / "settings.json"
        self._settings = AppSettings()
        self._load()

    @staticmethod
    def _detect_base_dir() -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).parent
        return Path(__file__).resolve().parent.parent

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    @property
    def settings_path(self) -> Path:
        return self._settings_path

    def get(self) -> AppSettings:
        return self._settings

    def get_dict(self) -> dict[str, Any]:
        return asdict(self._settings)

    def update(self, **kwargs: Any) -> None:
        valid_fields = set(AppSettings.__dataclass_fields__.keys())
        for key, value in kwargs.items():
            if key not in valid_fields:
                raise ValueError(f"Неизвестный параметр настроек: {key}")
            setattr(self._settings, key, value)
        self._save()

    def _load(self) -> None:
        if not self._settings_path.exists():
            self._save()
            return
        try:
            with open(self._settings_path, "r", encoding="utf-8") as file:
                data = json.load(file)
            defaults = asdict(AppSettings())
            defaults.update(data)
            self._settings = AppSettings(**defaults)
        except (json.JSONDecodeError, OSError, TypeError) as error:
            logging.getLogger("screen_translator").warning(
                "Не удалось загрузить settings.json: %s", error
            )
            self._settings = AppSettings()
            self._save()

    def _save(self) -> None:
        try:
            with open(self._settings_path, "w", encoding="utf-8") as file:
                json.dump(asdict(self._settings), file, ensure_ascii=False, indent=2)
        except OSError as error:
            raise RuntimeError(f"Не удалось сохранить настройки: {error}") from error

    def add_history_entry(self, source_text: str, translated_text: str) -> None:
        entry = HistoryEntry(
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            source_text=source_text,
            translated_text=translated_text,
        )
        history = list(self._settings.history)
        history.insert(0, asdict(entry))
        self._settings.history = history[:MAX_HISTORY_SIZE]
        self._save()

    def clear_history(self) -> None:
        self._settings.history = []
        self._save()

    def get_history(self) -> list[dict[str, str]]:
        return deepcopy(self._settings.history)

    def apply_autostart(self, enabled: bool) -> None:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE
            ) as key:
                if enabled:
                    if getattr(sys, "frozen", False):
                        command = f'"{sys.executable}"'
                    else:
                        command = f'"{sys.executable}" "{self._base_dir / "main.py"}"'
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
                else:
                    try:
                        winreg.DeleteValue(key, APP_NAME)
                    except FileNotFoundError:
                        pass
        except OSError as error:
            raise RuntimeError(f"Не удалось настроить автозапуск: {error}") from error

    def is_autostart_enabled(self) -> bool:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ
            ) as key:
                winreg.QueryValueEx(key, APP_NAME)
                return True
        except (FileNotFoundError, OSError):
            return False