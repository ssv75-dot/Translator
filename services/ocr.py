"""Распознавание текста на изображениях (OCR)."""

from __future__ import annotations

import os
import shutil
import sys
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    from services.logger import AppLogger


class OcrEngine(str, Enum):
    WINDOWS = "Windows OCR"
    PADDLE = "PaddleOCR"
    TESSERACT = "Tesseract"


def _app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def find_tesseract_executable(base_dir: Path | None = None) -> str | None:
    found = shutil.which("tesseract")
    if found:
        return found
    root = base_dir or _app_base_dir()
    candidates = [
        root / "resources" / "tesseract" / "tesseract.exe",
        root / "tesseract" / "tesseract.exe",
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
    ]
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", root))
        candidates.insert(0, meipass / "resources" / "tesseract" / "tesseract.exe")
        candidates.insert(1, root / "_internal" / "resources" / "tesseract" / "tesseract.exe")
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates.append(Path(local) / "Programs" / "Tesseract-OCR" / "tesseract.exe")
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def _configure_tesseract(tesseract_cmd: str) -> None:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    tessdata = Path(tesseract_cmd).parent / "tessdata"
    if tessdata.exists():
        os.environ.setdefault("TESSDATA_PREFIX", str(tessdata.parent))


class OcrService:
    def __init__(
        self,
        engine: str = OcrEngine.WINDOWS.value,
        logger: AppLogger | None = None,
        base_dir: Path | None = None,
    ) -> None:
        self._engine_name = engine
        self._logger = logger
        self._base_dir = base_dir or _app_base_dir()
        self._paddle = None
        self._tesseract_cmd = find_tesseract_executable(self._base_dir)

    def set_engine(self, engine: str) -> None:
        self._engine_name = engine
        self._paddle = None

    def recognize(self, image: Image.Image) -> str:
        if self._engine_name == OcrEngine.PADDLE.value:
            return self._recognize_paddle(image)
        if self._engine_name == OcrEngine.TESSERACT.value:
            return self._recognize_tesseract(image)
        return self._recognize_windows(image)

    def _recognize_windows(self, image: Image.Image) -> str:
        try:
            from services.windows_ocr import recognize as windows_recognize
            return windows_recognize(image)
        except RuntimeError as error:
            raise OcrError(str(error)) from error
        except OcrError:
            raise
        except Exception as error:
            if self._logger:
                self._logger.log_ocr_error("Ошибка Windows OCR", error)
            raise OcrError("Ошибка распознавания изображения.") from error

    def _recognize_paddle(self, image: Image.Image) -> str:
        try:
            if self._paddle is None:
                from paddleocr import PaddleOCR
                self._paddle = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
            import numpy as np
            result = self._paddle.ocr(np.array(image), cls=True)
            lines: list[str] = []
            if result and result[0]:
                for line in result[0]:
                    if line and len(line) > 1:
                        lines.append(str(line[1][0]))
            text = "\n".join(lines).strip()
            if not text:
                raise OcrError("Не удалось обнаружить текст.")
            return text
        except OcrError:
            raise
        except ImportError as error:
            raise OcrError("PaddleOCR не установлен. Выберите Windows OCR в настройках.") from error
        except Exception as error:
            if self._logger:
                self._logger.log_ocr_error("Ошибка PaddleOCR", error)
            raise OcrError("Ошибка распознавания изображения.") from error

    def _recognize_tesseract(self, image: Image.Image) -> str:
        cmd = self._tesseract_cmd or find_tesseract_executable(self._base_dir)
        if not cmd:
            raise OcrError(
                "Tesseract OCR не найден. Выберите Windows OCR в настройках "
                "или установите Tesseract: https://github.com/UB-Mannheim/tesseract/wiki"
            )
        try:
            import pytesseract
            _configure_tesseract(cmd)
            text = pytesseract.image_to_string(image, lang="eng").strip()
            if not text:
                raise OcrError("Не удалось обнаружить текст.")
            return text
        except OcrError:
            raise
        except Exception as error:
            if self._logger:
                self._logger.log_ocr_error("Ошибка Tesseract", error)
            raise OcrError("Ошибка распознавания изображения.") from error

    @staticmethod
    def check_availability(engine: str, base_dir: Path | None = None) -> dict:
        root = base_dir or _app_base_dir()
        messages: list[str] = []
        paddle_ok = False
        tesseract_ok = bool(find_tesseract_executable(root))
        windows_ok = False
        try:
            from services.windows_ocr import is_available
            windows_ok = is_available()
        except Exception:
            windows_ok = False
        try:
            import paddleocr  # noqa: F401
            paddle_ok = True
        except ImportError:
            pass

        if engine == OcrEngine.WINDOWS.value and not windows_ok:
            messages.append(
                "Windows OCR недоступен.\n"
                "Установите языковой пакет: Параметры → Время и язык → "
                "Язык → English → Параметры → Оптическое распознавание символов"
            )
        elif engine == OcrEngine.PADDLE.value and not paddle_ok:
            messages.append("PaddleOCR не установлен. Выберите Windows OCR в настройках.")
        elif engine == OcrEngine.TESSERACT.value and not tesseract_ok:
            messages.append(
                "Tesseract OCR не найден.\n"
                "Выберите Windows OCR в настройках или установите Tesseract."
            )

        return {
            "paddle": paddle_ok,
            "tesseract": tesseract_ok,
            "windows": windows_ok,
            "messages": messages,
        }


class OcrError(Exception):
    pass