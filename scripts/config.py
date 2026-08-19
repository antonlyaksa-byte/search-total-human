"""
Конфигурация проекта мониторинга
Search Total Human
"""

# Темы мониторинга
TOPICS = {
    "Total Experience": {
        "keywords_ru": [
            "total experience",
            "тотальный опыт",
            "обобщённый опыт",
            "TX стратегия",
            "общий опыт клиента и сотрудника",
        ],
        "keywords_en": [
            "total experience",
            "TX strategy",
            "total experience CX EX UX MX",
            "multiexperience strategy",
        ],
    },
    "Человекоцентричность": {
        "keywords_ru": [
            "человекоцентричность",
            "индекс человекоцентричности",
            "человекоцентричный подход",
            "человекоцентричность в бизнесе",
            "человекоцентричность HR",
        ],
        "keywords_en": [
            "human-centricity",
            "human-centered design",
            "human centricity index",
            "Industry 5.0 human-centric",
            "human-centric organization",
        ],
    },
}

# Ключевые источники для приоритетного отслеживания
PRIORITY_SOURCES = [
    "research.rosatomimpact.com",
    "rosatom-academy.ru",
    "gartner.com",
    "kpmg.com",
    "hse.ru",
    "mckinsey.com",
    "hbr.org",
    "deloitte.com",
    "ecopsy.ru",
]

# Типы материалов
MATERIAL_TYPES = ["Статья", "Отчёт", "Портал", "Пресс-релиз", "Исследование", "Видео"]

# Языки поиска
LANGUAGES = ["RU", "EN"]

# Пути к файлам (относительно корня проекта)
DATA_FILE = "data/monitoring_data.json"
OUTPUT_XLSX = "output/monitoring_base.xlsx"
OUTPUT_HTML = "output/monitoring_dashboard.html"
TEMPLATE_HTML = "templates/dashboard_template.html"
