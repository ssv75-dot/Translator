"""OCR через встроенный движок Windows 10/11 (Windows.Media.Ocr)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from PIL import Image
from winrt.windows.graphics.imaging import BitmapPixelFormat, SoftwareBitmap
from winrt.windows.globalization import Language
from winrt.windows.media.ocr import OcrEngine
from winrt.windows.storage.streams import DataWriter

# WinRT .get() нельзя вызывать из GUI-потока Qt (STA) — только из worker thread.
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="windows_ocr")


def is_available() -> bool:
    try:
        future = _executor.submit(_create_engine)
        return future.result(timeout=10) is not None
    except Exception:
        return False


def _create_engine() -> OcrEngine | None:
    engine = OcrEngine.try_create_from_language(Language("en-US"))
    if engine:
        return engine
    return OcrEngine.try_create_from_user_profile_languages()


def _pil_to_bitmap(image: Image.Image) -> SoftwareBitmap:
    rgba = image.convert("RGBA")
    writer = DataWriter()
    writer.write_bytes(rgba.tobytes())
    return SoftwareBitmap.create_copy_from_buffer(
        writer.detach_buffer(),
        BitmapPixelFormat.RGBA8,
        rgba.width,
        rgba.height,
    )


def _recognize_blocking(image: Image.Image) -> str:
    engine = _create_engine()
    if not engine:
        raise RuntimeError(
            "Windows OCR недоступен. Установите языковой пакет OCR:\n"
            "Параметры Windows → Время и язык → Язык → English → Параметры → OCR"
        )
    result = engine.recognize_async(_pil_to_bitmap(image)).get()
    text = (result.text or "").strip()
    if not text:
        raise RuntimeError("Не удалось обнаружить текст.")
    return text


def recognize(image: Image.Image) -> str:
    """Распознаёт текст, выполняя WinRT-вызовы в фоновом потоке."""
    future = _executor.submit(_recognize_blocking, image)
    return future.result(timeout=60)