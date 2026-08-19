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
│   ├── build_xlsx.py             # Генерация XLSX из JSON
│   └── build_dashboard.py        # Генерация HTML-дашборда из JSON
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

## Автоматизация

Проект подключён к Claude (проект "Search Total Human"). Еженедельный мониторинг можно включить через Claude — агент будет искать новые публикации, обновлять `monitoring_data.json` и пересобирать выходные файлы.
