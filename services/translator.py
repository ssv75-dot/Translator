"""Модуль перевода текста с поддержкой нескольких движков."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config.settings import AppSettings
    from services.logger import AppLogger


class TranslationError(Exception):
    """Ошибка перевода."""


class NetworkError(TranslationError):
    """Сетевая ошибка при переводе."""


def _exception_chain(error: BaseException):
    seen: set[int] = set()
    cur: BaseException | None = error
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        yield cur
        cur = cur.__cause__ or cur.__context__


def _ssl_exception_types() -> tuple[type, ...]:
    types: list[type] = []
    try:
        import ssl
        types.append(ssl.SSLError)
        if hasattr(ssl, "CertificateError"):
            types.append(ssl.CertificateError)
    except ImportError:
        pass
    try:
        from requests.exceptions import SSLError as RequestsSSLError
        types.append(RequestsSSLError)
    except ImportError:
        pass
    try:
        from urllib3.exceptions import SSLError as Urllib3SSLError
        types.append(Urllib3SSLError)
    except ImportError:
        pass
    return tuple(types)


def _network_exception_types() -> tuple[type, ...]:
    types: list[type] = [ConnectionError, TimeoutError]
    try:
        from requests.exceptions import (
            ConnectionError as RequestsConnectionError,
            ConnectTimeout,
            ReadTimeout,
            Timeout,
        )
        types.extend([RequestsConnectionError, ConnectTimeout, ReadTimeout, Timeout])
    except ImportError:
        pass
    try:
        from urllib3.exceptions import (
            NewConnectionError,
            ConnectTimeoutError,
            ReadTimeoutError,
        )
        types.extend([NewConnectionError, ConnectTimeoutError, ReadTimeoutError])
        try:
            from urllib3.exceptions import NameResolutionError
            types.append(NameResolutionError)
        except ImportError:
            pass
    except ImportError:
        pass
    try:
        import urllib.error
        types.append(urllib.error.URLError)
    except ImportError:
        pass
    return tuple(types)


_SSL_MARKERS = (
    "ssl",
    "tls",
    "certificate",
    "cert verify",
    "certificate verify failed",
    "unexpected_eof",
    "unexpected eof",
    "ssleoferror",
)

_OFFLINE_MARKERS = (
    "failed to establish",
    "name or service not known",
    "getaddrinfo failed",
    "network is unreachable",
    "no route to host",
    "nodename nor servname",
    "temporary failure in name resolution",
    "newconnectionerror",
    "nameresolutionerror",
    "errno 11001",
    "errno 10051",
    "errno 10065",
    "network is down",
)

_OFFLINE_ERRNOS = {
    101,
    51,
    65,
    11001,
    11002,
    10051,
    10065,
    10060,
}


def _is_ssl_error(error: BaseException) -> bool:
    ssl_types = _ssl_exception_types()
    for exc in _exception_chain(error):
        if ssl_types and isinstance(exc, ssl_types):
            return True
        msg = str(exc).lower()
        if any(m in msg for m in _SSL_MARKERS):
            return True
    return False


def _is_network_offline_error(error: BaseException) -> bool:
    """Detect real offline/DNS/connectivity failures. Does not treat bare 'connection' as offline."""
    if _is_ssl_error(error):
        return False

    net_types = _network_exception_types()
    for exc in _exception_chain(error):
        if isinstance(exc, urllib.error.HTTPError):
            continue
        if net_types and isinstance(exc, net_types):
            # URLError wraps many reasons including SSL - check reason
            reason = getattr(exc, "reason", None)
            if reason is not None and _is_ssl_error(
                reason if isinstance(reason, BaseException) else Exception(str(reason))
            ):
                return False
            # Generic URLError without a connectivity reason is not necessarily offline
            if isinstance(exc, urllib.error.URLError) and reason is None:
                continue
            return True
        if isinstance(exc, OSError):
            if getattr(exc, "errno", None) in _OFFLINE_ERRNOS:
                return True
        msg = str(exc).lower()
        if any(m in msg for m in _OFFLINE_MARKERS):
            return True
        if "internet" in msg:
            return True
        # Max retries with connection-establishment wording (SSL already excluded)
        if "max retries exceeded" in msg and (
            "newconnectionerror" in msg
            or "failed to establish" in msg
            or "nameresolution" in msg
        ):
            return True
    return False



def _raise_transport_error(error: BaseException) -> None:
    """Re-raise URL/socket failures as SSL TranslationError or offline NetworkError."""
    if _is_ssl_error(error):
        raise TranslationError(
            "Ошибка защищённого соединения с сервисом перевода."
        ) from error
    if _is_network_offline_error(error):
        raise NetworkError("Нет подключения к Интернету.") from error
    # URLError with HTTP/other reasons, etc.
    raise TranslationError("Не удалось выполнить перевод.") from error

TRANSLATE_TIMEOUT_SEC = 15


def _call_with_timeout(func, *args, **kwargs):
    """Best-effort timeout for translators that use sockets/requests without one."""
    import socket

    previous = socket.getdefaulttimeout()
    socket.setdefaulttimeout(TRANSLATE_TIMEOUT_SEC)
    try:
        return func(*args, **kwargs)
    finally:
        socket.setdefaulttimeout(previous)



@dataclass(frozen=True)
class TranslationResult:
    """Результат перевода в унифицированном формате."""

    source: str
    target: str
    translated: str
    original: str


class BaseTranslator(ABC):
    """Базовый класс для всех переводчиков."""

    @abstractmethod
    def translate(self, text: str, source: str, target: str) -> TranslationResult:
        pass


class DeepTranslatorEngine(BaseTranslator):
    """Перевод через библиотеку deep-translator."""

    def translate(self, text: str, source: str, target: str) -> TranslationResult:
        from deep_translator import GoogleTranslator

        src = "auto" if source == "auto" else source
        translator = GoogleTranslator(source=src, target=target)

        def _do():
            return translator.translate(text)

        translated = _call_with_timeout(_do)
        detected = src if src != "auto" else "en"
        return TranslationResult(detected, target, translated, text)


class LibreTranslateEngine(BaseTranslator):
    """Перевод через LibreTranslate API."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def translate(self, text: str, source: str, target: str) -> TranslationResult:
        payload = json.dumps({
            "q": text,
            "source": source if source != "auto" else "en",
            "target": target,
            "format": "text",
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base_url}/translate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=TRANSLATE_TIMEOUT_SEC) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as error:
            _raise_transport_error(error)
        translated = data.get("translatedText", "")
        if not translated:
            raise TranslationError("Не удалось выполнить перевод.")
        return TranslationResult(source, target, translated, text)


class DeepLEngine(BaseTranslator):
    """Перевод через DeepL API."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def translate(self, text: str, source: str, target: str) -> TranslationResult:
        if not self._api_key:
            raise TranslationError("Укажите API-ключ DeepL в настройках.")
        from deep_translator import DeeplTranslator

        src = None if source == "auto" else source.upper()
        translator = DeeplTranslator(
            api_key=self._api_key, source=src, target=target.upper(), use_free_api=True
        )
        translated = _call_with_timeout(translator.translate, text)
        return TranslationResult(source, target, translated, text)


class YandexEngine(BaseTranslator):
    """Перевод через Yandex Translate API."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def translate(self, text: str, source: str, target: str) -> TranslationResult:
        if not self._api_key:
            raise TranslationError("Укажите API-ключ Yandex в настройках.")
        from deep_translator import YandexTranslator

        src = source if source != "auto" else "en"
        translator = YandexTranslator(api_key=self._api_key, source=src, target=target)
        translated = _call_with_timeout(translator.translate, text)
        return TranslationResult(src, target, translated, text)


class OpenAIEngine(BaseTranslator):
    """Перевод через OpenAI Chat Completions API."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def translate(self, text: str, source: str, target: str) -> TranslationResult:
        if not self._api_key:
            raise TranslationError("Укажите API-ключ OpenAI в настройках.")
        lang_map = {"ru": "русский", "en": "английский", "auto": "исходный язык"}
        target_name = lang_map.get(target, target)
        payload = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": f"Переведи текст на {target_name}. Верни только перевод без пояснений.",
                },
                {"role": "user", "content": text},
            ],
            "temperature": 0.2,
        }).encode("utf-8")
        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=TRANSLATE_TIMEOUT_SEC) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as error:
            _raise_transport_error(error)
        translated = data["choices"][0]["message"]["content"].strip()
        return TranslationResult(source, target, translated, text)


class TranslatorService:
    """Фасад для выбора и вызова нужного переводчика."""

    ENGINE_MAP = {
        "Deep Translator": "deep",
        "LibreTranslate": "libre",
        "OpenAI": "openai",
        "DeepL": "deepl",
        "Yandex": "yandex",
    }

    def __init__(self, settings: AppSettings, logger: AppLogger | None = None) -> None:
        self._settings = settings
        self._logger = logger

    def update_settings(self, settings: AppSettings) -> None:
        self._settings = settings

    def translate(self, text: str) -> TranslationResult:
        if not text.strip():
            raise TranslationError("Текст не найден.")
        engine = self._create_engine()
        source = self._settings.source_language
        target = self._settings.target_language
        try:
            return engine.translate(text, source, target)
        except NetworkError:
            raise
        except TranslationError:
            raise
        except Exception as error:
            if self._logger:
                self._logger.log_translation_error("Ошибка вызова переводчика", error)
            if _is_ssl_error(error):
                raise TranslationError(
                    "Ошибка защищённого соединения с сервисом перевода."
                ) from error
            if _is_network_offline_error(error):
                raise NetworkError("Нет подключения к Интернету.") from error
            raise TranslationError("Не удалось выполнить перевод.") from error

    def _create_engine(self) -> BaseTranslator:
        name = self._settings.translator
        if name == "LibreTranslate":
            return LibreTranslateEngine(self._settings.libretranslate_url)
        if name == "OpenAI":
            return OpenAIEngine(self._settings.openai_api_key)
        if name == "DeepL":
            return DeepLEngine(self._settings.deepl_api_key)
        if name == "Yandex":
            return YandexEngine(self._settings.yandex_api_key)
        return DeepTranslatorEngine()
