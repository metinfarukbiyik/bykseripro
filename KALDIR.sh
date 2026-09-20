#!/usr/bin/env bash
# macOS kaldırma — BYK Seri Baskı Pro
set -euo pipefail

APP="/Applications/BYKSeriBaskiPro.app"
OLD_APP="/Applications/SeriBarkodEtiketBaski.app"
SUPPORT="$HOME/Library/Application Support/BiyikDev/BYKSeriBaskiPro"
OLD_SUPPORT="$HOME/Library/Application Support/BiyikDev/SeriBarkodEtiketBaski"
DISPLAY_NAME="BYK Seri Baskı Pro"
echo "$DISPLAY_NAME kaldırılıyor..."

for path in "$APP" "$OLD_APP"; do
  if [[ -d "$path" ]]; then
    rm -rf "$path"
    echo "  Silindi: $path"
  fi
done

rm -f "$HOME/Desktop/$DISPLAY_NAME" \
      "$HOME/Desktop/${DISPLAY_NAME}.command" \
      "$HOME/Desktop/Seri Barkod Etiket Baskı" \
      "$HOME/Desktop/Seri Barkod Etiket Baskı.command" 2>/dev/null || true
if command -v osascript >/dev/null 2>&1; then
  osascript -e "tell application \"Finder\" to try
  delete file \"${DISPLAY_NAME}\" of desktop
end try" 2>/dev/null || true
  osascript -e 'tell application "Finder" to try
  delete file "Seri Barkod Etiket Baskı" of desktop
end try' 2>/dev/null || true
fi

read -r -p "Config / Excel veri klasörünü de sil? (e/H): " ANS
if [[ "$ANS" == "e" || "$ANS" == "E" ]]; then
  rm -rf "$SUPPORT" "$OLD_SUPPORT" 2>/dev/null || true
  echo "  Veri klasörü silindi."
else
  echo "  Veri korundu: $SUPPORT"
fi

echo "Kaldırma tamamlandı."
