"""
README görsellerini üretir → assets/readme/

Etiket örnekleri uygulamanın kendi yerleşim / önizleme motoruyla çizilir,
yani yazıcıdan çıkacak etiketle birebir aynıdır.

    python tools/readme_images.py
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

from label_preview import render_label_image  # noqa: E402
from tspl_builder import LabelData, LabelSettings  # noqa: E402

OUT = ROOT / "assets" / "readme"
NAVY = (27, 51, 82)
NAVY_DARK = (16, 32, 54)
GOLD = (184, 150, 46)
SOFT = (245, 247, 250)

FONT_BOLD = (
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "arialbd.ttf",
    "DejaVuSans-Bold.ttf",
)
FONT_REG = (
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "arial.ttf",
    "DejaVuSans.ttf",
)


def _font(candidates: tuple[str, ...], size: int) -> ImageFont.FreeTypeFont:
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _card(label_img: Image.Image, width: int, pad: int = 28) -> Image.Image:
    """Etiketi gölgeli kart olarak açık zemine yerleştirir."""
    ratio = width / label_img.width
    lab = label_img.resize(
        (width, int(label_img.height * ratio)), Image.Resampling.LANCZOS
    )
    w, h = lab.width + pad * 2, lab.height + pad * 2
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [pad, pad + 6, pad + lab.width, pad + lab.height + 6], 10, fill=(16, 32, 54, 70)
    )
    canvas = Image.alpha_composite(canvas, shadow.filter(ImageFilter.GaussianBlur(9)))
    mask = Image.new("L", lab.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, lab.width - 1, lab.height - 1], 8, fill=255)
    canvas.paste(lab, (pad, pad), mask)
    return canvas


def _sample_labels() -> dict[str, Image.Image]:
    base = LabelSettings(brand_text="ACME ÜRETİM", brand_enabled=True, font_item=2)
    square = render_label_image(
        LabelData("SN2026100245", "AK-554433", "Motor kapağı · 10-200-33", "Model X200 — Lot 7"),
        replace(base, brand_position="top", brand_style="box"),
    )
    narrow = render_label_image(
        LabelData("SN2026100246", "M-77812", "Conta seti", "Depo B-14"),
        replace(
            base, width_mm=100, height_mm=40, margin_mm=2, ak_position="side",
            brand_position="bottom", brand_style="inverse",
            gap_after_barcode_mm=0.8, gap_between_barcodes_mm=2, gap_after_text_mm=1,
        ),
    )
    qr = render_label_image(
        LabelData("https://biyik.dev/byk-seri-baski-pro", "", "QR ile ürün sayfası", ""),
        replace(
            base, width_mm=60, height_mm=60, margin_mm=3, barcode_type="QRCODE",
            barcode_height_mm=28, show_main_text=False, brand_style="lines",
            brand_position="bottom", qr_cell=0,
        ),
    )
    return {"square": square, "narrow": narrow, "qr": qr}


def banner(labels: dict[str, Image.Image]) -> None:
    W, H = 1280, 440
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    # Dikey degrade
    for y in range(H):
        t = y / H
        c = tuple(int(NAVY[i] * (1 - t) + NAVY_DARK[i] * t) for i in range(3))
        d.line([(0, y), (W, y)], fill=c)
    # Arka plan barkod deseni (soluk)
    x = 760
    for i, wbar in enumerate((6, 3, 3, 9, 3, 6, 12, 3, 6, 3, 9, 6, 3, 12, 6, 3) * 3):
        if i % 2 == 0:
            d.rectangle([x, 0, x + wbar, H], fill=(34, 61, 96))
        x += wbar + 4
    d.rectangle([0, H - 6, W, H], fill=GOLD)

    logo = Image.open(ROOT / "assets" / "app.png").convert("RGBA").resize((96, 96))
    img.paste(logo, (72, 78), logo)
    d.text((72, 196), "BYK Seri Baskı Pro", font=_font(FONT_BOLD, 54), fill="white")
    d.text(
        (74, 266),
        "Excel’den seri barkod etiketlerine — tek tıkla.",
        font=_font(FONT_REG, 26),
        fill=(201, 211, 224),
    )
    chips = ("Windows", "macOS", "TSPL yazıcılar", "Otomatik güncelleme")
    x = 74
    f = _font(FONT_BOLD, 17)
    for text in chips:
        tw = int(d.textlength(text, font=f))
        d.rounded_rectangle([x, 330, x + tw + 28, 366], 18, outline=GOLD, width=2)
        d.text((x + 14, 338), text, font=f, fill=(240, 226, 186))
        x += tw + 42

    card = _card(labels["square"], 300)
    img.paste(card, (W - card.width - 70, (H - card.height) // 2), card)
    img.save(OUT / "banner.png", optimize=True)


def showcase(labels: dict[str, Image.Image]) -> None:
    for name, width in (("square", 320), ("narrow", 520), ("qr", 260)):
        card = _card(labels[name], width)
        bg = Image.new("RGBA", card.size, SOFT + (255,))
        Image.alpha_composite(bg, card).convert("RGB").save(
            OUT / f"label-{name}.png", optimize=True
        )


def brand_styles() -> None:
    lab = LabelData("SN2026100247", "", "", "")
    rows = []
    for style in ("plain", "box", "inverse", "lines"):
        s = LabelSettings(
            width_mm=70, height_mm=24, margin_mm=1.5, brand_text="ACME ÜRETİM",
            brand_style=style, brand_position="bottom", barcode_height_mm=7,
            show_main_text=False, font_brand=2,
        )
        rows.append(_card(render_label_image(lab, s), 300, pad=16))
    w = sum(r.width for r in rows)
    out = Image.new("RGBA", (w, rows[0].height), SOFT + (255,))
    x = 0
    for r in rows:
        out.alpha_composite(r, (x, 0))
        x += r.width
    out.convert("RGB").save(OUT / "brand-styles.png", optimize=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    labels = _sample_labels()
    banner(labels)
    showcase(labels)
    brand_styles()
    for p in sorted(OUT.glob("*.png")):
        print(f"{p.relative_to(ROOT)}  {Image.open(p).size}  {p.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
