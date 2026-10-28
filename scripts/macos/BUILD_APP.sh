#!/usr/bin/env bash
# macOS .app derleme (BUILD_EXE.bat eşdeğeri)
# NOT: Bu script yalnızca macOS'ta çalışır.
set -euo pipefail
cd "$(dirname "$0")/../.."  # scripts/macos → proje kökü

echo "========================================"
echo " BIYIK.DEV — BYK Seri Baskı Pro (.app)"
echo "========================================"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Hata: Bu script yalnızca macOS'ta çalışır."
  echo "Windows için scripts\\windows\\BUILD_EXE.bat / BUILD_RELEASE.bat kullanın."
  exit 1
fi

PYTHON="${PYTHON:-python3}"
"$PYTHON" -m pip install -r requirements.txt pyinstaller -q

echo "[1/3] İkonlar (app.ico + iconset → app.icns)..."
"$PYTHON" tools/prepare_icons.py
if command -v iconutil >/dev/null 2>&1; then
  iconutil -c icns assets/app.iconset -o assets/app.icns
  echo "  app.icns oluşturuldu."
else
  echo "  Uyarı: iconutil yok; .app ikonsuz derlenebilir."
fi

echo "[2/3] PyInstaller (macOS .app)..."
"$PYTHON" -m PyInstaller --noconfirm packaging/BYKSeriBaskiPro-macOS.spec

APP="dist/BYKSeriBaskiPro.app"
if [[ ! -d "$APP" ]]; then
  echo "Derleme başarısız: $APP yok."
  exit 1
fi

if command -v codesign >/dev/null 2>&1; then
  echo "[3/3] Ad-hoc codesign..."
  codesign --force --deep --sign - "$APP" 2>/dev/null || true
else
  echo "[3/3] codesign atlandı."
fi

echo
echo "Tamam: $APP"
echo "Kurulum: scripts/macos/KURULUM.command"
echo "Dağıtım: scripts/macos/BUILD_RELEASE_MAC.command"
echo
