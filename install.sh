#!/usr/bin/env bash
# Установка Search Total Human на Ubuntu.
# Скачайте файл, сделайте исполняемым и запустите:
#   chmod +x install.sh && ./install.sh
# Каталог установки можно передать первым аргументом.
set -euo pipefail

REPO_URL="https://github.com/antonlyaksa-byte/search-total-human.git"
MIN_MAJOR=3
MIN_MINOR=9

say() { printf '%s\n' "$*"; }
die() { printf 'Ошибка: %s\n' "$*" >&2; exit 1; }

PYTHON=""

run_apt() {
  if command -v sudo >/dev/null 2>&1 && [[ "$(id -u)" -ne 0 ]]; then
    sudo "$@"
  else
    "$@"
  fi
}

apt_update() {
  say "Обновляю списки пакетов apt"
  run_apt apt-get update
}

pick_python() {
  local candidate
  for candidate in python3.12 python3.11 python3.10 python3.9 python3; do
    if command -v "$candidate" >/dev/null 2>&1 \
      && "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 9) else 1)'; then
      PYTHON="$candidate"
      return 0
    fi
  done
  return 1
}

install_deadsnakes() {
  local ver
  say "apt не установил подходящий Python. Пробую deadsnakes PPA."
  run_apt apt-get install -y software-properties-common
  run_apt add-apt-repository -y ppa:deadsnakes/ppa
  run_apt apt-get update
  for ver in 3.12 3.11 3.10 3.9; do
    if run_apt apt-get install -y "python${ver}" "python${ver}-venv"; then
      return 0
    fi
  done
  return 1
}

if [[ "$(uname -s)" != "Linux" ]]; then
  die "Скрипт рассчитан на Linux."
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/requirements.txt" && -f "$SCRIPT_DIR/scripts/monitor.py" ]]; then
  ROOT="$SCRIPT_DIR"
else
  ROOT="${1:-$HOME/search-total-human}"
fi

need_apt() {
  local missing=()
  command -v python3 >/dev/null 2>&1 || missing+=(python3)
  command -v git >/dev/null 2>&1 || missing+=(git)
  if command -v python3 >/dev/null 2>&1 && ! python3 -m venv --help >/dev/null 2>&1; then
    missing+=(python3-venv)
  fi
  if ((${#missing[@]})); then
    say "Ставлю пакеты: ${missing[*]}"
    apt_update
    run_apt apt-get install -y "${missing[@]}"
  fi
}

if ! pick_python; then
  need_apt || say "Установка python3 через apt не удалась."
  pick_python || true
fi
if [[ -z "$PYTHON" ]]; then
  install_deadsnakes || die "Не удалось поставить Python ${MIN_MAJOR}.${MIN_MINOR}+ ни через apt, ни через deadsnakes."
  pick_python || die "Python ${MIN_MAJOR}.${MIN_MINOR}+ не найден после установки."
fi
say "Python: $($PYTHON --version 2>&1) ($PYTHON)"

if ! command -v git >/dev/null 2>&1; then
  apt_update
  run_apt apt-get install -y git
fi

if [[ ! -f "$ROOT/requirements.txt" ]]; then
  command -v git >/dev/null 2>&1 || die "Не найден git, репозиторий не скачать."
  say "Скачиваю проект в $ROOT"
  git clone "$REPO_URL" "$ROOT"
fi

[[ -f "$ROOT/requirements.txt" ]] || die "В $ROOT нет requirements.txt"
[[ -f "$ROOT/scripts/monitor.py" ]] || die "В $ROOT нет scripts/monitor.py"

if [[ ! -x "$ROOT/venv/bin/python3" ]]; then
  if ! "$PYTHON" -m venv --help >/dev/null 2>&1; then
    apt_update
    run_apt apt-get install -y "$(basename "$PYTHON")-venv" || install_deadsnakes
  fi
  say "Создаю виртуальное окружение $ROOT/venv"
  "$PYTHON" -m venv "$ROOT/venv"
else
  say "Виртуальное окружение уже есть: $ROOT/venv"
fi

say "Ставлю зависимости"
"$ROOT/venv/bin/python3" -m pip install --upgrade pip
"$ROOT/venv/bin/python3" -m pip install -r "$ROOT/requirements.txt"

CRON="0 3 * * 0 cd \"$ROOT\" && \"$ROOT/venv/bin/python3\" scripts/monitor.py"
say ""
say "Готово. Поиск вручную:"
say "  cd \"$ROOT\" && \"$ROOT/venv/bin/python3\" scripts/monitor.py"
say ""
say "Строка cron, воскресенье в 03:00:"
say "$CRON"
say ""
say "Добавить её в crontab: crontab -e"
