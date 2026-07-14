"""Захват выбранной области экрана."""

from __future__ import annotations

from dataclasses import dataclass

import mss
from PIL import Image


@dataclass(frozen=True)
class ScreenRegion:
    left: int
    top: int
    width: int
    height: int

    def to_mss_monitor(self) -> dict[str, int]:
        return {
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
        }


@dataclass(frozen=True)
class DesktopCapture:
    image: Image.Image
    left: int
    top: int
    width: int
    height: int


class ScreenshotService:
    def capture_desktop(self) -> DesktopCapture:
        """Делает снимок всего рабочего стола (все мониторы)."""
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[0]
                shot = sct.grab(monitor)
                image = Image.frombytes("RGB", shot.size, shot.rgb)
                return DesktopCapture(
                    image=image,
                    left=monitor["left"],
                    top=monitor["top"],
                    width=monitor["width"],
                    height=monitor["height"],
                )
        except Exception as error:
            raise ScreenshotError("Не удалось сделать снимок экрана.") from error

    def capture_region(self, region: ScreenRegion) -> Image.Image:
        if region.width < 2 or region.height < 2:
            raise ScreenshotError("Слишком маленькая область для снимка.")
        try:
            with mss.mss() as sct:
                shot = sct.grab(region.to_mss_monitor())
                return Image.frombytes("RGB", shot.size, shot.rgb)
        except Exception as error:
            raise ScreenshotError("Не удалось сделать снимок экрана.") from error


class ScreenshotError(Exception):
    pass