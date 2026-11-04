"""
Еженедельный поиск новых публикаций.

Использование:
    python scripts/monitor.py --dry-run
    python scripts/monitor.py
    python scripts/monitor.py --push

Читает data/monitoring_data.json и scripts/config.py, ищет новые материалы,
открывает страницы и дописывает только те, которых ещё нет в базе.
Ключи и модели не используются. Существующие записи не меняются.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import date
from urllib.parse import urlparse, urlunparse

import httpx
import trafilatura
from ddgs import DDGS
from deep_translator import GoogleTranslator, MyMemoryTranslator

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_dashboard import build_dashboard  # noqa: E402
from build_xlsx import build_xlsx  # noqa: E402
from config import PRIORITY_SOURCES, TOPICS  # noqa: E402

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(PROJECT_ROOT, "data", "monitoring_data.json")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
LOGIN_MARKERS = (
    "join linkedin",
    "sign in to linkedin",
    "authwall",
    "login to continue",
    "войдите, чтобы",
    "sign in to view",
)


def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("monitoring_data.json должен быть массивом")
    return data


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def normalize_url(url):
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme.lower() or "https", host, path, "", parsed.query, ""))


def normalize_title(title):
    return re.sub(r"\s+", " ", title or "").casefold().strip()


def host_of(url):
    return urlparse(url).netloc.lower().removeprefix("www.")


def is_priority(url):
    host = host_of(url)
    return any(host == source or host.endswith("." + source) for source in PRIORITY_SOURCES)


def duplicate_reason(candidate, data):
    """Совпадение по нормализованному URL или по названию."""
    url = normalize_url(candidate.get("url", ""))
    title = normalize_title(candidate.get("title", ""))
    for item in data:
        if item.get("url") and normalize_url(item["url"]) == url:
            return "url"
        if title and normalize_title(item.get("title", "")) == title:
            return "title"
    return None


def search_queries():
    queries = []
    for topic in TOPICS.values():
        queries.extend(topic["keywords_ru"])
        queries.extend(topic["keywords_en"])
    for source in PRIORITY_SOURCES:
        queries.append(f"site:{source} total experience")
        queries.append(f"site:{source} человекоцентричность")
    queries.append("site:linkedin.com Total Experience")
    queries.append("site:linkedin.com человекоцентричность")
    seen = set()
    unique = []
    for query in queries:
        key = query.casefold()
        if key not in seen:
            seen.add(key)
            unique.append(query)
    return unique


def iter_search_hits(queries):
    """Листает выдачу страница за страницей и отдаёт новые ссылки по одной."""
    seen = set()
    with DDGS() as ddgs:
        for query in queries:
            page = 1
            while True:
                try:
                    results = ddgs.text(query, page=page) or []
                except Exception as exc:
                    print(f"Поиск не удался ({query}, стр. {page}): {exc}", flush=True)
                    break
                if not results:
                    break
                added = 0
                for item in results:
                    url = item.get("href") or item.get("url") or ""
                    if not url.startswith("http"):
                        continue
                    key = normalize_url(url)
                    if key in seen:
                        continue
                    seen.add(key)
                    added += 1
                    yield {
                        "url": url,
                        "title": (item.get("title") or "").strip(),
                        "snippet": (item.get("body") or "").strip(),
                        "query": query,
                        "priority": is_priority(url),
                    }
                if added == 0:
                    break
                page += 1
                time.sleep(1.2)
            time.sleep(1.2)


def looks_like_login_wall(url, text):
    blob = f"{url}\n{text}".casefold()
    if any(marker in blob for marker in LOGIN_MARKERS) and len(text) < 800:
        return True
    lowered = url.casefold()
    return "linkedin.com" in lowered and ("/login" in lowered or "authwall" in lowered)


def fetch_page(client, url):
    response = client.get(url)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if "html" not in content_type and "text/" not in content_type and content_type:
        return None
    html = response.text
    final_url = str(response.url)
    text = trafilatura.extract(
        html,
        url=final_url,
        include_comments=False,
        favor_precision=True,
    ) or ""
    text = re.sub(r"\s+", " ", text).strip()
    if looks_like_login_wall(final_url, text):
        print(f"Пропуск, страница закрыта входом: {final_url}")
        return None
    if len(text) < 280:
        print(f"Пропуск, слишком мало текста: {final_url}")
        return None
    metadata = trafilatura.extract_metadata(html, default_url=final_url)
    title = ""
    sitename = ""
    published = ""
    if metadata is not None:
        title = (metadata.title or "").strip()
        sitename = (getattr(metadata, "sitename", None) or "").strip()
        published = (getattr(metadata, "date", None) or "").strip()
    return {
        "url": final_url,
        "title": title,
        "text": text,
        "sitename": sitename,
        "date": published,
    }


def choose_topic(page):
    blob = f"{page.get('title', '')}\n{page.get('snippet', '')}\n{page.get('text', '')}".casefold()
    scores = {}
    for name, topic in TOPICS.items():
        score = 0
        for keyword in topic["keywords_ru"] + topic["keywords_en"]:
            if keyword.casefold() in blob:
                score += len(keyword)
        scores[name] = score
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return None
    return best


def detect_type(url, title, text):
    blob = f"{url} {title}".casefold()
    if any(mark in blob for mark in ("youtube.com", "youtu.be", "vimeo.com")):
        return "Видео"
    if "linkedin.com" in blob:
        return "Пост" if len(text) < 1200 else "Статья"
    if url.casefold().endswith(".pdf") or any(
        word in blob for word in ("white paper", "whitepaper", "отчёт", "отчет", "report")
    ):
        return "Отчёт"
    if any(word in blob for word in ("пресс-релиз", "press release", "press-release")):
        return "Пресс-релиз"
    if any(word in blob for word in ("исследован", "research", "study")):
        return "Исследование"
    path = urlparse(url).path.strip("/")
    if not path or path in ("index.html", "index.htm"):
        return "Портал"
    return "Статья"


def detect_lang(text):
    letters = [char for char in text.casefold() if char.isalpha()]
    if not letters:
        return "EN"
    cyrillic = sum(1 for char in letters if "а" <= char <= "я" or char == "ё")
    return "RU" if cyrillic / len(letters) >= 0.3 else "EN"


def extract_year(page):
    for source in (page.get("date") or "", page.get("url") or "", (page.get("text") or "")[:800]):
        match = re.search(r"(?:19|20)\d{2}", source)
        if match:
            return match.group(0)
    return ""


def lead_summary(text):
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    summary = " ".join(part for part in parts[:2] if part).strip()
    if len(summary) > 500:
        summary = summary[:500].rsplit(" ", 1)[0].rstrip(".,;:") + "…"
    return summary


def translate_chunk(chunk):
    attempts = (
        lambda: MyMemoryTranslator(source="en-GB", target="ru-RU").translate(chunk),
        lambda: GoogleTranslator(source="auto", target="ru").translate(chunk),
    )
    for attempt in attempts:
        try:
            translated = (attempt() or "").strip()
        except Exception as exc:
            print(f"Перевод не удался: {exc}", flush=True)
            continue
        if translated and detect_lang(translated) == "RU":
            return translated
    return ""


def to_russian(text):
    """Переводит текст на русский. Уже русский текст не трогает. Без ключа API."""
    cleaned = (text or "").strip()
    if not cleaned or detect_lang(cleaned) == "RU":
        return cleaned
    chunks = []
    rest = cleaned
    while rest:
        if len(rest) <= 450:
            chunks.append(rest)
            break
        cut = rest.rfind(" ", 0, 450)
        if cut < 80:
            cut = 450
        chunks.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    parts = [translate_chunk(chunk) for chunk in chunks]
    if not all(parts):
        return ""
    return " ".join(parts).strip()


def build_record(page):
    topic = choose_topic(page)
    title = (page.get("title") or "").strip()
    summary = to_russian(lead_summary(page.get("text") or ""))
    if topic is None or len(title) < 8 or len(summary) < 20:
        return None
    source = (page.get("sitename") or host_of(page["url"])).strip()
    return {
        "topic": topic,
        "title": title,
        "type": detect_type(page["url"], title, page.get("text") or ""),
        "summary": summary,
        "source": source,
        "url": page["url"],
        "lang": detect_lang(f"{title}\n{page.get('text') or ''}"),
        "year": extract_year(page),
    }


def collect_new_records(data, pages):
    records = []
    seen = list(data)
    for page in pages:
        record = build_record(page)
        if record is None:
            print(f"Не по теме: {page.get('title') or page['url']}")
            continue
        reason = duplicate_reason(record, seen)
        if reason:
            print(f"Дубль по {reason}: {record['title']}")
            continue
        records.append(record)
        seen.append(record)
    return records


def append_records(data, records):
    next_id = max((item.get("id", 0) for item in data), default=0) + 1
    today = date.today().isoformat()
    for offset, record in enumerate(records):
        if duplicate_reason(record, data):
            continue
        data.append(
            {
                "id": next_id + offset,
                "topic": record["topic"],
                "title": record["title"],
                "type": record["type"],
                "summary": record["summary"],
                "source": record["source"],
                "url": record["url"],
                "lang": record["lang"],
                "year": record["year"],
                "added": today,
            }
        )
    return data


def git_publish(count, titles):
    short = "; ".join(titles[:4])
    if len(titles) > 4:
        short += "…"
    message = f"Add {count} new sources: {short}"
    subprocess.run(
        ["git", "add", "data/monitoring_data.json", "output/monitoring_dashboard.html"],
        cwd=PROJECT_ROOT,
        check=True,
    )
    subprocess.run(["git", "commit", "-m", message], cwd=PROJECT_ROOT, check=True)
    subprocess.run(["git", "push", "origin", "master"], cwd=PROJECT_ROOT, check=True)
    print(f"Отправлено в origin/master: {message}")


def run(args):
    data = load_data()
    queries = search_queries()
    limit_text = str(args.limit) if args.limit else "без ограничения"
    print(f"Запросов: {len(queries)}. Уже в базе: {len(data)}. Лимит: {limit_text}", flush=True)

    records = []
    checked = 0
    with httpx.Client(
        timeout=20,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "ru,en;q=0.8"},
    ) as client:
        for hit in iter_search_hits(queries):
            if duplicate_reason(hit, data) or duplicate_reason(hit, records):
                continue
            checked += 1
            try:
                page = fetch_page(client, hit["url"])
            except Exception as exc:
                print(f"Не открылась {hit['url']}: {exc}", flush=True)
                continue
            if page is None:
                continue
            page["snippet"] = hit["snippet"]
            if not page["title"]:
                page["title"] = hit["title"]
            found = collect_new_records(data + records, [page])
            records.extend(found)
            if args.limit and len(records) >= args.limit:
                records = records[: args.limit]
                break
            time.sleep(0.4)
    print(f"Проверено новых ссылок: {checked}. Подходящих: {len(records)}", flush=True)

    if args.dry_run:
        for record in records:
            print(f"- [{record['topic']}] {record['title']} | {record['url']}")
        print(f"Пробный запуск: нашлось бы {len(records)}, база не изменена.")
        return 0

    if not records:
        print("Новых публикаций нет, база не изменена.")
        return 0

    before = len(data)
    updated = append_records(data, records)
    added = updated[before:]
    if not added:
        print("Все найденные записи уже есть в базе.")
        return 0

    save_data(updated)
    build_dashboard(updated)
    build_xlsx(updated)
    print(f"Добавлено записей: {len(added)}")
    for record in added:
        print(f"- [{record['topic']}] {record['title']}")

    if args.push:
        git_publish(len(added), [record["title"] for record in added])
    return 0


def parse_args():
    parser = argparse.ArgumentParser(description="Поиск новых источников для Search Total Human")
    parser.add_argument("--dry-run", action="store_true", help="Искать и открывать страницы, ничего не записывать")
    parser.add_argument("--push", action="store_true", help="После новых записей сделать commit и push в master")
    parser.add_argument("--limit", type=int, default=None, help="Сколько новых записей добавить за этот запуск")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit должен быть больше нуля")
    return args


if __name__ == "__main__":
    try:
        raise SystemExit(run(parse_args()))
    except RuntimeError as exc:
        print(exc)
        raise SystemExit(1)
