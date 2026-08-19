#!/bin/bash
# Weekly source-monitoring run for Search Total Human.
# Runs on the VPS via cron. Uses a long-lived Claude Code OAuth token
# (subscription-based, no per-token API billing) and a GitHub deploy key
# for push access — independent of the claude.ai cloud routine / GitHub App.
set -euo pipefail

REPO_DIR="/root/search-total-human"
TOKEN_FILE="/root/.config/search-total-human/oauth_token"
LOG_DIR="/root/search-total-human-logs"
LOG_FILE="$LOG_DIR/$(date +%Y-%m-%d_%H-%M-%S).log"

mkdir -p "$LOG_DIR"
cd "$REPO_DIR"

export CLAUDE_CODE_OAUTH_TOKEN
CLAUDE_CODE_OAUTH_TOKEN="$(cat "$TOKEN_FILE")"

git pull origin master --quiet

PROMPT=$(cat <<'PROMPT_EOF'
Ты работаешь в репозитории search-total-human (текущая рабочая директория) — проект мониторинга публикаций по темам Total Experience (TX) и Человекоцентричность (человекоцентричный подход, индекс человекоцентричности, Industry 5.0 human-centric).

Задача: найти новые публикации (статьи, отчёты, порталы, пресс-релизы, исследования), которых ещё нет в базе, и добавить их.

1. Прочитай data/monitoring_data.json — текущая база (массив объектов). Прочитай scripts/config.py — там ключевые слова (RU/EN) и приоритетные источники PRIORITY_SOURCES: research.rosatomimpact.com, rosatom-academy.ru, gartner.com, kpmg.com, hse.ru, mckinsey.com, hbr.org, deloitte.com, ecopsy.ru.

2. С помощью WebSearch/WebFetch найди 3-8 новых, реально существующих публикаций по темам TX и человекоцентричность за последние недели/месяцы. Приоритет — источники из PRIORITY_SOURCES и крупные издания (Gartner, KPMG, McKinsey, HBR, Deloitte, HSE, Росатом и т.п.), но подойдут и другие релевантные находки.
   - Обязательно включи отдельные запросы вида `site:linkedin.com Total Experience` и `site:linkedin.com человекоцентричность`, чтобы найти публичные статьи/посты на LinkedIn по теме.
   - Каждую ссылку подтверди реальным поиском — НЕ выдумывай URL. Если не можешь подтвердить существование страницы, не добавляй её.
   - Для ссылок на linkedin.com: перед добавлением попробуй WebFetch — если страница требует входа в аккаунт и содержимое не открывается (пустая заглушка/форма логина вместо текста поста), не добавляй эту ссылку. Добавляй только те посты/статьи LinkedIn, чьё содержимое реально удалось прочитать.
   - Не добавляй дубликаты: сверяй по полю url с уже существующими записями (и по смыслу — заголовок/источник).

3. Для каждой новой публикации добавь объект в конец массива в data/monitoring_data.json (см. существующие записи как образец формата):
   - id: следующий по порядку номер (максимальный существующий id + 1, далее по возрастанию)
   - topic: "Total Experience" или "Человекоцентричность"
   - title: точное название материала
   - type: один из ["Статья", "Отчёт", "Портал", "Пресс-релиз", "Исследование", "Видео", "Пост"] (используй "Пост" для коротких постов LinkedIn/соцсетей, "Статья" — для полноценных статей, в т.ч. LinkedIn-статей)
   - summary: краткое описание на русском (1-2 предложения), даже если материал на английском
   - source: издание/автор
   - url: точная ссылка
   - lang: "RU" или "EN"
   - year: год публикации (строка)
   - added: сегодняшняя дата в формате YYYY-MM-DD

4. Сохрани файл — валидный JSON с отступом в 2 пробела, как в исходном файле. Не удаляй и не изменяй существующие записи.

5. Обнови output/monitoring_dashboard.html: подставь новый массив данных в переменную `const DATA = [...]` внутри <script> (сохраняя формат объектов — с полем added, двойные кавычки, отступ 2 пробела, как в data/monitoring_data.json), и обнови строку `document.getElementById('lastUpdate').textContent = '...'` на сегодняшнюю дату. Если в окружении есть Python с openpyxl, можно вместо этого просто запустить `python3 scripts/build_dashboard.py`.

6. Закоммить изменения (git add data/monitoring_data.json output/monitoring_dashboard.html) с сообщением вида "Add N new sources: <краткое перечисление тем>" и запушь: git push origin master. Git уже настроен и имеет доступ на запись — просто закоммить и запушь напрямую, никаких обходных путей не требуется.

Важно: если за неделю не нашлось ни одной новой релевантной и проверенной публикации — не добавляй ничего и не делай пустой коммит, просто заверши работу без изменений.
PROMPT_EOF
)

claude -p "$PROMPT" \
  --allowedTools "Bash Read Write Edit Glob Grep WebSearch WebFetch" \
  >> "$LOG_FILE" 2>&1

echo "Run finished, log: $LOG_FILE"

# Keep only the last 20 logs
ls -1t "$LOG_DIR" | tail -n +21 | xargs -r -I{} rm -f "$LOG_DIR/{}"
