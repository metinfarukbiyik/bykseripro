@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo BYK Seri Baskı Pro — Biyik.dev
echo Bagimliliklar kontrol ediliyor...
python -m pip install -r requirements.txt -q
if errorlevel 1 (
  echo pip hatasi.
  pause
  exit /b 1
)
python app.py %*
