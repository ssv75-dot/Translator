# Screen Translator

Настольное приложение для Windows 10/11: перевод выделенного английского текста и текста с экрана (OCR) с показом результата в небольшом окне поверх всех приложений.

## Возможности

- Перевод выделенного текста через `Ctrl+Shift+T` (настраивается)
- Захват области экрана и OCR через `Ctrl+Shift+S`
- Окно перевода без рамки, поверх всех окон
- Системный трей, автозапуск с Windows
- Несколько переводчиков: Deep Translator, LibreTranslate, OpenAI, DeepL, Yandex
- OCR: PaddleOCR (предпочтительно) и Tesseract
- История последних 100 переводов
- Логирование ошибок в папку `logs/`

## Требования

- Windows 10 / 11
- Python 3.12+
- Подключение к Интернету (для перевода)

### OCR (опционально, но рекомендуется)

**PaddleOCR** (устанавливается через pip):

```bash
pip install paddleocr paddlepaddle
```

**Tesseract OCR** (резервный вариант):

1. Скачайте установщик: https://github.com/tesseract-ocr/tesseract
2. Установите и добавьте `tesseract` в PATH

## Установка

```bash
cd "O:\Проекты VIBE\Translator"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Запуск

```bash
python main.py
```

После запуска приложение можно свернуть в трей. Закрытие окна не завершает программу — она продолжает работать в системном трее.

### Горячие клавиши по умолчанию

| Действие | Сочетание |
|----------|-----------|
| Перевести выделенный текст | `Ctrl+Shift+T` |
| Выделить область экрана | `Ctrl+Shift+S` |

## Настройка

Настройки хранятся в `settings.json` в корне проекта. Их можно изменить через окно «Настройки» или вручную.

Пример:

```json
{
  "translator": "Deep Translator",
  "ocr": "PaddleOCR",
  "source_language": "auto",
  "target_language": "ru",
  "hotkey_translate": "Ctrl+Shift+T",
  "hotkey_capture": "Ctrl+Shift+S"
}
```

Для OpenAI, DeepL и Yandex укажите API-ключи в настройках.

## Сборка в EXE

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name ScreenTranslator main.py
```

Готовый файл: `dist\ScreenTranslator.exe`

> Для OCR в собранном exe может потребоваться отдельная настройка путей к Tesseract и моделям PaddleOCR.

## Структура проекта

```
main.py
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