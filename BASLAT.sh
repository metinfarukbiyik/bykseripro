#!/usr/bin/env bash
# BYK Seri Baskı Pro — macOS / Linux başlatıcı (BASLAT.bat eşdeğeri)
set -euo pipefail
cd "$(dirname "$0")"

echo "BYK Seri Baskı Pro — Biyik.dev"
echo "Bağımlılıklar kontrol ediliyor..."

PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Python3 bulunamadı. https://www.python.org/downloads/"
  exit 1
fi

"$PYTHON" -m pip install -r requirements.txt -q
exec "$PYTHON" app.py "$@"
