#!/usr/bin/env bash
# macOS kurulum — .app → /Applications (+ isteğe bağlı masaüstü kısayol)
set -euo pipefail
cd "$(dirname "$0")"

APP_NAME="BYKSeriBaskiPro.app"
DISPLAY_NAME="BYK Seri Baskı Pro"
SUPPORT_DIR="BYKSeriBaskiPro"
SRC=""
if [[ -d "dist/$APP_NAME" ]]; then
  SRC="dist/$APP_NAME"
elif [[ -d "$APP_NAME" ]]; then
  SRC="$APP_NAME"
fi

if [[ -z "$SRC" ]]; then
  echo "Uygulama bulunamadı."
  echo "Önce BUILD_APP.command (veya ./BUILD_APP.sh) çalıştırın."
  exit 1
fi

DEST="/Applications/$APP_NAME"
echo "========================================"
echo " $DISPLAY_NAME — Kurulum"
echo " BIYIK.DEV (macOS)"
echo "========================================"
echo "Kaynak: $SRC"
echo "Hedef : $DEST"
echo

if [[ -d "$DEST" ]]; then
  echo "Eski sürüm kaldırılıyor..."
  rm -rf "$DEST"
fi
# Eski ürün adı kalıntısı
rm -rf "/Applications/SeriBarkodEtiketBaski.app" 2>/dev/null || true

cp -R "$SRC" "$DEST"
xattr -cr "$DEST" 2>/dev/null || true
if command -v codesign >/dev/null 2>&1; then
  codesign --force --deep --sign - "$DEST" 2>/dev/null || true
fi

SUPPORT="$HOME/Library/Application Support/BiyikDev/$SUPPORT_DIR"
mkdir -p "$SUPPORT"
if [[ ! -f "$SUPPORT/config.json" && -f "config.json" ]]; then
  cp config.json "$SUPPORT/" 2>/dev/null || true
fi
if [[ ! -f "$SUPPORT/Barkod.xlsx" && -f "Barkod.xlsx" ]]; then
  cp Barkod.xlsx "$SUPPORT/" 2>/dev/null || true
fi

cat > "$SUPPORT/KALDIR.command" <<EOF
#!/bin/bash
rm -rf "/Applications/${APP_NAME}"
rm -f "\$HOME/Desktop/${DISPLAY_NAME}" \
      "\$HOME/Desktop/${DISPLAY_NAME}.command" 2>/dev/null
osascript -e 'tell application "Finder" to try
  delete file "${DISPLAY_NAME}" of desktop
end try' 2>/dev/null || true
# Eski kısayol
rm -f "\$HOME/Desktop/Seri Barkod Etiket Baskı" 2>/dev/null || true
echo "Uygulama kaldırıldı. Config: ~/Library/Application Support/BiyikDev/${SUPPORT_DIR}"
read -r -p "Config klasörünü de silmek ister misiniz? (e/H): " ANS
if [[ "\$ANS" == "e" || "\$ANS" == "E" ]]; then
  rm -rf "\$HOME/Library/Application Support/BiyikDev/${SUPPORT_DIR}"
fi
EOF
chmod +x "$SUPPORT/KALDIR.command"

DESK="$HOME/Desktop/$DISPLAY_NAME"
rm -f "$DESK" "$DESK.command" \
      "$HOME/Desktop/Seri Barkod Etiket Baskı" \
      "$HOME/Desktop/Seri Barkod Etiket Baskı.command" 2>/dev/null || true
if command -v osascript >/dev/null 2>&1; then
  osascript <<EOF
tell application "Finder"
  try
    delete file "${DISPLAY_NAME}" of desktop
  end try
  try
    delete file "Seri Barkod Etiket Baskı" of desktop
  end try
  make new alias file to POSIX file "$DEST" at desktop with properties {name:"${DISPLAY_NAME}"}
end tell
EOF
else
  ln -sf "$DEST" "$DESK"
fi

echo
echo "Kurulum tamamlandı."
echo "  Uygulama: $DEST"
echo "  Veri    : $SUPPORT"
echo "  Masaüstü: $DESK"
echo
read -r -p "Şimdi uygulamayı açmak ister misiniz? (E/h): " RUN
if [[ "${RUN:-E}" == "E" || "${RUN:-E}" == "e" || -z "$RUN" ]]; then
  open "$DEST"
fi
