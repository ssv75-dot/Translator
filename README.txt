# Screen Translator

Настольное приложение для Windows 10/11: перевод выделенного английского текста и текста с экрана (OCR) с показом результата в небольшом окне поверх всех приложений.

## Возможности

- Перевод выделенного текста через `Ctrl+Shift+T` (настраивается)
- Захват области экрана и OCR через `Ctrl+Shift+S`
- Окно перевода без рамки, поверх всех окон
- Системный трей, автозапуск с Windows
- Несколько переводчиков: Deep Translator, LibreTranslate, OpenAI, DeepL, Yandex
- OCR: Windows OCR, Tesseract, PaddleOCR
- История последних 100 переводов
- Логирование ошибок в папку `logs/`

## Готовые сборки

После сборки доступны два варианта:

| Вариант | Файл | Описание |
|---------|------|----------|
| **Установщик** | `dist\installer\ScreenTranslatorSetup.exe` | Устанавливает приложение в `%LocalAppData%\Programs\Screen Translator` (или выбранную папку), создаёт ярлыки в меню «Пуск» и (опционально) на рабочем столе |
| **Portable** | `ScreenTranslatorPortable.exe` (+ папка `_internal` рядом) или `dist\ScreenTranslatorPortable\` | Запуск без установки: скопируйте всю папку на флешку или диск и запускайте `ScreenTranslatorPortable.exe` |

> Portable — onedir-сборка: рядом с `ScreenTranslatorPortable.exe` должна лежать папка `_internal`. Одного exe недостаточно.

### Горячие клавиши по умолчанию

| Действие | Сочетание |
|----------|-----------|
| Перевести выделенный текст | `Ctrl+Shift+T` |
| Выделить область экрана | `Ctrl+Shift+S` |

После запуска приложение можно свернуть в трей. Закрытие окна не завершает программу — она продолжает работать в системном трее.

## Требования

- Windows 10 / 11
- Python 3.12+ (только для разработки из исходников)
- Подключение к Интернету (для перевода)

### OCR (опционально)

**Windows OCR** — встроен в Windows 10/11 (рекомендуется по умолчанию).

**PaddleOCR** (через pip):

```bash
pip install paddleocr paddlepaddle
```

**Tesseract OCR**:

1. Скачайте установщик: https://github.com/tesseract-ocr/tesseract
2. Установите и добавьте `tesseract` в PATH

## Установка из исходников (разработка)

```bash
cd "O:\Проекты VIBE\Translator"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Запуск из исходников

```bash
python main.py
```

## Настройка

Настройки хранятся в `settings.json` рядом с исполняемым файлом (или в корне проекта при запуске из исходников). Их можно изменить через окно «Настройки» или вручную.

Пример:

```json
{
  "translator": "Deep Translator",
  "ocr": "Windows OCR",
  "source_language": "auto",
  "target_language": "ru",
  "hotkey_translate": "Ctrl+Shift+T",
  "hotkey_capture": "Ctrl+Shift+S"
}
```

Для OpenAI, DeepL и Yandex укажите API-ключи в настройках.

## Сборка portable и установщика

Требуется [Inno Setup 6](https://jrsoftware.org/isinfo.php) для компиляции установщика.

```powershell
.venv\Scripts\activate
pip install pyinstaller
powershell -ExecutionPolicy Bypass -File scripts\build_release.ps1
```

Вручную:

```bash
pyinstaller --noconfirm ScreenTranslator.spec
```

Portable: `dist\ScreenTranslatorPortable\ScreenTranslatorPortable.exe`

Установщик (после установки Inno Setup):

```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\ScreenTranslator.iss
```

Готовый установщик: `dist\installer\ScreenTranslatorSetup.exe`

## Структура проекта

```
main.py
ScreenTranslator.spec
installer/
    ScreenTranslator.iss
scripts/
    build_release.ps1
ui/
    main_window.py
    settings_window.py
    popup_window.py
    screenshot_overlay.py
services/
    translator.py
    ocr.py
    clipboard.py
    screenshot.py
    hotkeys.py
config/
    settings.py
resources/
logs/
```

## Примечания

- Глобальные горячие клавиши работают через библиотеку `keyboard`; на некоторых системах может потребоваться запуск от имени администратора.
- По умолчанию перевод выполняется через Deep Translator (Google API без браузера).
- Логи ошибок OCR, перевода и сети: `logs/screen_translator.log`
