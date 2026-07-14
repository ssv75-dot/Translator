"""Модуль логирования ошибок OCR, перевода и сети."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


class AppLogger:
    """Настраивает логгер приложения с ротацией файлов."""

    def __init__(self, logs_dir: Path) -> None:
        self._logs_dir = logs_dir
        self._logs_dir.mkdir(parents=True, exist_ok=True)
        self._logger = logging.getLogger("screen_translator")
        self._configure()

    def _configure(self) -> None:
        if self._logger.handlers:
            return
        self._logger.setLevel(logging.DEBUG)
        log_file = self._logs_dir / "screen_translator.log"
        file_handler = RotatingFileHandler(
            log_file, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        self._logger.addHandler(file_handler)
        self._logger.addHandler(console_handler)

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    def log_ocr_error(self, message: str, exc: Exception | None = None) -> None:
        self._logger.error("OCR: %s", message, exc_info=exc)

    def log_translation_error(self, message: str, exc: Exception | None = None) -> None:
        self._logger.error("Перевод: %s", message, exc_info=exc)

    def log_network_error(self, message: str, exc: Exception | None = None) -> None:
        self._logger.error("Сеть: %s", message, exc_info=exc)