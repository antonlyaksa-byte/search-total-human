"""
Генерация HTML-дашборда из базы данных мониторинга.

Использование:
    python scripts/build_dashboard.py

Читает data/monitoring_data.json, создаёт output/monitoring_dashboard.html
"""

import json
import os
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(PROJECT_ROOT, "data", "monitoring_data.json")
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "output", "monitoring_dashboard.html")
TEMPLATE_FILE = os.path.join(PROJECT_ROOT, "templates", "dashboard_template.html")


def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def build_dashboard(data):
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template = f.read()

    # Вставляем данные и дату обновления
    js_data = json.dumps(data, ensure_ascii=False, indent=2)
    today = datetime.now().strftime("%Y-%m-%d")

    html = template.replace("/* __DATA_PLACEHOLDER__ */", f"const DATA = {js_data};")
    html = html.replace("__LAST_UPDATE__", today)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Дашборд создан: {OUTPUT_FILE} ({len(data)} записей)")


if __name__ == "__main__":
    data = load_data()
    build_dashboard(data)
