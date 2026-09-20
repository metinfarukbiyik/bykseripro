"""Uygulama ikonlarını tek kaynaktan üretir.

Kaynak (source of truth):
  assets/app.png  — uygulama kimliği (masaüstü / başlat / .app / pencere)

Çıktılar:
  assets/app.ico       — Windows exe + kısayol + title bar
  assets/app.iconset/  — macOS iconutil girdisi → app.icns

UI rozeti (biyik_badge.png) ve whatsapp.png bu script tarafından
üretilmez; arayüz görselleridir, sistem ikonu değildir.

Kullanım:
  python tools/prepare_icons.py
  # macOS'ta ardından:
  #   iconutil -c icns assets/app.iconset -o assets/app.icns
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
SRC = ASSETS / "app.png"
ICO = ASSETS / "app.ico"
ICONSET = ASSETS / "app.iconset"

# Windows: title bar (16) → Start/Desktop (32/48) → yüksek DPI / exe (256)
WIN_SIZES = (16, 24, 32, 48, 64, 128, 256)

# Apple iconutil beklenen boyutlar
MAC_SIZES = [
    (16, "icon_16x16.png"),
    (32, "icon_16x16@2x.png"),
    (32, "icon_32x32.png"),
    (64, "icon_32x32@2x.png"),
    (128, "icon_128x128.png"),
    (256, "icon_128x128@2x.png"),
    (256, "icon_256x256.png"),
    (512, "icon_256x256@2x.png"),
    (512, "icon_512x512.png"),
    (1024, "icon_512x512@2x.png"),
]


def _load_source() -> Image.Image:
    if SRC.exists():
        return Image.open(SRC).convert("RGBA")
    badge = ASSETS / "biyik_badge.png"
    if badge.exists():
        print(f"Uyarı: {SRC.name} yok; yedek: {badge.name}")
        return Image.open(badge).convert("RGBA")
    raise SystemExit(f"Kaynak yok: {SRC}")


def _square_rgba(img: Image.Image, side: int) -> Image.Image:
    """Kareye sığdır; şeffaf arka planla ortala (padding)."""
    img = img.convert("RGBA")
    if img.size == (side, side):
        return img
    # Önce en uzun kenara göre ölçekle, sonra canvas'a yerleştir
    src = img.copy()
    src.thumbnail((side, side), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    x = (side - src.width) // 2
    y = (side - src.height) // 2
    canvas.paste(src, (x, y), src)
    return canvas


def write_ico(src: Image.Image) -> None:
    # En yüksek çözünürlükten Pillow alt boyutları üretir
    master = _square_rgba(src, max(WIN_SIZES))
    master.save(ICO, format="ICO", sizes=[(s, s) for s in WIN_SIZES])
    # Doğrulama
    check = Image.open(ICO)
    got = sorted(check.info.get("sizes") or {check.size})
    print(f"OK {ICO.relative_to(ROOT)}  boyutlar={[s[0] for s in got]}")


def write_iconset(src: Image.Image) -> None:
    ICONSET.mkdir(parents=True, exist_ok=True)
    for side, name in MAC_SIZES:
        _square_rgba(src, side).save(ICONSET / name, format="PNG")
    print(f"OK {ICONSET.relative_to(ROOT)}/  ({len(MAC_SIZES)} dosya)")
    print("macOS: iconutil -c icns assets/app.iconset -o assets/app.icns")


def main() -> None:
    src = _load_source()
    write_ico(src)
    write_iconset(src)


if __name__ == "__main__":
    main()
