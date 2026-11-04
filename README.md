# Search Total Human

Мониторинг публикаций и исследований по темам **Total Experience** и **Человекоцентричность**.

## Темы

- **Total Experience (TX)** — стратегия объединения CX, EX, UX, MX
- **Человекоцентричность** — методологии, индексы (в т.ч. индекс Росатома), корпоративные практики

## Структура проекта

```
search-total-human/
├── data/
│   └── monitoring_data.json      # База данных источников (JSON)
├── output/
│   ├── monitoring_base.xlsx      # Таблица (генерируется)
│   └── monitoring_dashboard.html # Дашборд (генерируется)
├── scripts/
│   ├── config.py                 # Конфигурация: темы, ключевые слова, источники
│   ├── monitor.py                # Поиск новых публикаций и дозапись JSON
│   ├── build_xlsx.py             # Генерация XLSX из JSON
│   ├── build_dashboard.py        # Генерация HTML-дашборда из JSON
│   ├── google_sheets_script.gs   # Скрипт Google Таблицы (не нужен для локального запуска)
│   └── run_local.ps1             # Локальный запуск мониторинга на Windows
├── templates/
│   └── dashboard_template.html   # Шаблон дашборда
├── requirements.txt
└── README.md
```

## Быстрый старт

```bash
pip install -r requirements.txt

# Пересобрать таблицу
python scripts/build_xlsx.py

# Пересобрать дашборд
python scripts/build_dashboard.py

# Найти новые публикации (ничего не пишет на диск)
python scripts/monitor.py --dry-run

# Найти, открыть страницы и дописать базу. Ключи не нужны.
python scripts/monitor.py
```

## Как добавить новый источник

Добавьте запись в `data/monitoring_data.json`:

```json
{
  "id": 29,
  "topic": "Total Experience",
  "title": "Название статьи",
  "type": "Статья",
  "summary": "Краткое описание на русском",
  "source": "Издание",
  "url": "https://...",
  "lang": "RU",
  "year": "2026",
  "added": "2026-08-19"
}
```

Затем пересоберите выходные файлы:

```bash
python scripts/build_xlsx.py
python scripts/build_dashboard.py
```

## Локальный запуск

Проект работает на этом компьютере. Сервер, ключи и модели не нужны. Нужны Python 3.11 и интернет, когда идёт поиск новых страниц.

```powershell
cd "C:\Users\tosha\Desktop\Проекты Claude Code\search-total-human"
python -m pip install -r requirements.txt
python scripts\build_dashboard.py
python scripts\build_xlsx.py
```

Дашборд открывается файлом `output\monitoring_dashboard.html`. Таблица — `output\monitoring_base.xlsx`.

Поиск новых публикаций (база меняется только если нашлось что-то новое):

```powershell
python scripts\monitor.py
```

Пробный прогон без записи: `python scripts\monitor.py --dry-run`.

Краткое содержание всегда сохраняется по-русски. Если страница на другом языке, первые предложения переводятся без ключа. Язык материала в колонке «Язык» при этом остаётся языком источника.

Раз в неделю то же самое делает `scripts\run_local.ps1`, лог пишется в папку `logs`. В Планировщике заданий Windows укажите:

```text
powershell -ExecutionPolicy Bypass -File "C:\Users\tosha\Desktop\Проекты Claude Code\search-total-human\scripts\run_local.ps1"
```

Флаг `--push` по-прежнему может отправить JSON и дашборд в GitHub, но для локальной работы он не нужен. Google Таблица из `scripts\google_sheets_script.gs` читает файл с GitHub, поэтому сама по себе после переноса не обновляется. Локальные HTML и Excel от GitHub не зависят.
