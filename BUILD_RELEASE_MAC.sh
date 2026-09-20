#!/usr/bin/env bash
# macOS dağıtım paketi (BUILD_RELEASE.bat eşdeğeri)
set -euo pipefail
cd "$(dirname "$0")"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Hata: Bu script yalnızca macOS'ta çalışır."
  exit 1
fi

VER="$(tr -d '[:space:]' < VERSION 2>/dev/null || echo 1.1.1)"
echo "========================================"
echo " BIYIK.DEV — BYK Seri Baskı Pro v$VER"
echo "========================================"

./BUILD_APP.sh

OUT="release/BYKSeriBaskiPro_v${VER}_macOS"
rm -rf release 2>/dev/null || true
mkdir -p "$OUT"

cp -R "dist/BYKSeriBaskiPro.app" "$OUT/"
cp DAGITIM.txt "$OUT/OKU_BENI.txt"
cp KURULUM.sh KALDIR.sh KURULUM.command KALDIR.command "$OUT/"
chmod +x "$OUT/KURULUM.sh" "$OUT/KALDIR.sh" \
         "$OUT/KURULUM.command" "$OUT/KALDIR.command"
echo "$VER" > "$OUT/VERSION.txt"

ZIP="release/BYKSeriBaskiPro_v${VER}_macOS.zip"
rm -f "$ZIP"
ditto -c -k --sequesterRsrc --keepParent "$OUT" "$ZIP"

echo
echo "TAMAM"
echo "Paylaşılacak: $ZIP"
echo
echo "Alıcı:"
echo "  1) Zip’i açar"
echo "  2) BYKSeriBaskiPro.app’e çift tıklar"
echo "     veya KURULUM.command ile /Applications’a kurar"
echo
echo "Gatekeeper: İlk açılışta sağ tık → Aç"
echo
