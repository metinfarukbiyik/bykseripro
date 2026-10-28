"""
Etiket metni — ölçüm, satır kaydırma ve grafik (bitmap) çizimi.

Grafik modunda metin TrueType ile çizilip yazıcıya BITMAP olarak gider:
Türkçe karakterler doğru basılır ve genişlik piksel kesinliğinde bilinir,
bu yüzden uzun metinler de tam ortalanır. Önizleme aynı görüntüyü kullanır.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Callable

from PIL import Image, ImageDraw, ImageFont

_FONT_CANDIDATES = (
    "arialbd.ttf",
    "Arial Bold.ttf",
    "Arial.ttf",
    "arial.ttf",
    "segoeuib.ttf",
    "segoeui.ttf",
    "DejaVuSans-Bold.ttf",
    "DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
)

# Satır yüksekliğinin ne kadarı yazı boyutu (em) olarak kullanılır
_EM_RATIO = 0.82


@lru_cache(maxsize=32)
def load_font(px: int) -> ImageFont.ImageFont:
    px = max(6, int(px))
    for name in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, px)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=px)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


def graphic_font(line_h: int) -> ImageFont.ImageFont:
    return load_font(int(round(line_h * _EM_RATIO)))


def graphic_text_width(text: str, line_h: int) -> int:
    font = graphic_font(line_h)
    try:
        return int(round(font.getlength(text)))
    except AttributeError:
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0]


def render_text_image(text: str, line_h: int, width: int | None = None) -> Image.Image:
    """Siyah metin / beyaz zemin, 'L' modunda; yükseklik = satır yüksekliği."""
    font = graphic_font(line_h)
    tw = graphic_text_width(text, line_h)
    w = max(1, width if width is not None else tw)
    img = Image.new("L", (w, max(1, line_h)), 255)
    draw = ImageDraw.Draw(img)
    # Dikeyde ortala: yazı kutusunu satır içine yerleştir
    ascent, descent = font.getmetrics() if hasattr(font, "getmetrics") else (line_h, 0)
    y = max(0, (line_h - (ascent + descent)) // 2)
    draw.text(((w - tw) // 2, y), text, fill=0, font=font)
    return img


def tspl_bitmap_payload(img: Image.Image) -> tuple[int, int, bytes]:
    """
    TSPL BITMAP verisi: (genişlik_bayt, yükseklik, veri).
    TSPL'de bit 0 = siyah nokta, 1 = beyaz.
    """
    bw = img.convert("L").point(lambda p: 0 if p < 128 else 255, mode="1")
    w, h = bw.size
    width_bytes = (w + 7) // 8
    padded = Image.new("1", (width_bytes * 8, h), 1)
    padded.paste(bw, (0, 0))
    # PIL '1' modu: 1 = beyaz → TSPL ile aynı anlam
    return width_bytes, h, padded.tobytes()


def wrap_text(
    text: str, max_w: int, measure: Callable[[str], int], max_lines: int
) -> list[str] | None:
    """
    Metni kelime sınırlarından max_w içine sığacak satırlara böler.
    max_lines aşılırsa None döner (çağıran daha küçük font dener).
    Tek kelime satıra sığmıyorsa karakter bazında bölünür.
    """
    text = " ".join((text or "").split())
    if not text:
        return []
    if measure(text) <= max_w:
        return [text]
    if max_lines <= 1:
        return None

    lines: list[str] = []
    current = ""
    for word in text.split(" "):
        candidate = f"{current} {word}" if current else word
        if measure(candidate) <= max_w:
            current = candidate
            continue
        if current:
            lines.append(current)
        # Kelime tek başına da sığmıyorsa parçala
        while measure(word) > max_w and len(word) > 1:
            cut = len(word)
            while cut > 1 and measure(word[:cut]) > max_w:
                cut -= 1
            lines.append(word[:cut])
            word = word[cut:]
        current = word
        if len(lines) > max_lines:
            return None
    if current:
        lines.append(current)
    return lines if len(lines) <= max_lines else None


def truncate_to_width(text: str, max_w: int, measure: Callable[[str], int]) -> str:
    """Son çare: sığmayan metni '…' ile kısalt (sayfa dışına taşmasın)."""
    if measure(text) <= max_w:
        return text
    ell = "..."
    cut = len(text)
    while cut > 0 and measure(text[:cut].rstrip() + ell) > max_w:
        cut -= 1
    return (text[:cut].rstrip() + ell) if cut > 0 else ""


def credit_icon(h: int) -> Image.Image:
    """
    Program imzası ikonu: barkod tarayıcı vizörü — dört köşe çerçevesi ve
    farklı kalınlıkta barkod çizgileri. Tek renk ve yazıcı noktasına hizalı
    çizilir → termal baskıda keskin çıkar. 'L' modunda döner (0 = siyah).
    """
    h = max(12, int(h))
    u = max(1, round(h / 22))  # çizgi birimi (203 DPI'da 1 nokta)
    w = round(h * 1.36)
    img = Image.new("1", (w, h), 1)
    d = ImageDraw.Draw(img)

    # Köşe çerçeveleri: her köşede yatay + dikey kol
    arm = max(3 * u, round(h * 0.28))
    for x, y, sx, sy in ((0, 0, 1, 1), (w - 1, 0, -1, 1), (0, h - 1, 1, -1), (w - 1, h - 1, -1, -1)):
        xe, ye = x + sx * (arm - 1), y + sy * (arm - 1)
        xt, yt = x + sx * (u - 1), y + sy * (u - 1)
        d.rectangle([min(x, xe), min(y, yt), max(x, xe), max(y, yt)], fill=0)
        d.rectangle([min(x, xt), min(y, ye), max(x, xt), max(y, ye)], fill=0)

    # Barkod: çizgi / boşluk genişlikleri u katı, vizör içinde ortalı
    pattern = (2, 1, 1, 1, 3, 1, 1, 2, 1, 1, 2, 1, 1, 1, 3, 1, 2)
    left, right = 3 * u + 1, w - 3 * u - 1
    x = left + max(0, (right - left - sum(pattern) * u) // 2)
    top, bot = 3 * u + 1, h - 3 * u - 2
    for i, k in enumerate(pattern):
        bw = k * u
        if x + bw > right:
            break
        if i % 2 == 0:
            d.rectangle([x, top, x + bw - 1, bot], fill=0)
        x += bw
    return img.convert("L")
