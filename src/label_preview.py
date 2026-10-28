"""Etiket görsel önizlemesi (Pillow + Code128/39/93/EAN + QR)."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw, ImageOps, ImageTk

from text_render import credit_icon, render_text_image
from tspl_builder import (
    LabelData,
    LabelSettings,
    LayoutBarcode,
    compute_layout,
    normalize_barcode_type,
)


def _fallback_bars(data: str, target_w: int, target_h: int) -> Image.Image:
    img = Image.new("RGB", (max(1, target_w), max(1, target_h)), "white")
    draw = ImageDraw.Draw(img)
    x = 2
    seed = sum(ord(c) for c in data) or 1
    while x < target_w - 2:
        bar_w = 1 + (seed + x) % 3
        if (seed + x) % 2 == 0:
            draw.rectangle([x, 0, x + bar_w - 1, target_h - 1], fill="black")
        x += bar_w + 1
    return img


def _make_linear(data: str, code_type: str, target_w: int, target_h: int) -> Image.Image:
    """1D barkod görüntüsü."""
    try:
        import barcode
        from barcode.writer import ImageWriter

        mapping = {
            "128": "code128",
            "39": "code39",
            "93": "code93",
            "EAN13": "ean13",
            "EAN8": "ean8",
        }
        name = mapping.get(normalize_barcode_type(code_type), "code128")
        payload = data
        if name == "ean13":
            digits = "".join(c for c in data if c.isdigit())
            if len(digits) < 12:
                digits = digits.zfill(12)
            payload = digits[:12]
        elif name == "ean8":
            digits = "".join(c for c in data if c.isdigit())
            if len(digits) < 7:
                digits = digits.zfill(7)
            payload = digits[:7]

        code = barcode.get(name, payload, writer=ImageWriter())
        buf = BytesIO()
        code.write(
            buf,
            options={
                "module_width": 0.4,
                "module_height": 14,
                "quiet_zone": 0.5,
                "font_size": 0,
                "text_distance": 1,
                "write_text": False,
            },
        )
        buf.seek(0)
        img = Image.open(buf).convert("L")
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
        img = img.resize((max(1, target_w), max(1, target_h)), Image.Resampling.NEAREST)
        return img.convert("RGB")
    except Exception:
        return _fallback_bars(data, target_w, target_h)


def _make_qr(data: str, target_side: int) -> Image.Image:
    try:
        import qrcode

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=4,
            border=1,
        )
        qr.add_data(data or "0")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        side = max(8, target_side)
        return img.resize((side, side), Image.Resampling.NEAREST)
    except Exception:
        return _fallback_bars(data, target_side, target_side)


def _render_symbol(bc: LayoutBarcode, target_w: int, target_h: int) -> Image.Image:
    if bc.kind == "qr" or normalize_barcode_type(bc.code_type) == "QRCODE":
        side = max(target_w, target_h)
        return _make_qr(bc.data, side)
    return _make_linear(bc.data, bc.code_type, target_w, target_h)


def render_label_image(label: LabelData, settings: LabelSettings) -> Image.Image:
    """
    Etiketi yazıcı çözünürlüğünde (1 piksel = 1 dot) çizer.
    Barkod ve metinler TSPL'deki x/y değerleriyle aynı yere konur → kağıtla birebir.
    """
    layout = compute_layout(label, settings)
    w, h = max(1, layout.width), max(1, layout.height)
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)

    # Kenar boşluğu kılavuzu (yalnız ekranda)
    m = layout.margin
    if m > 0 and w > 2 * m and h > 2 * m:
        for x in range(m, w - m, 12):
            draw.line([x, m, min(x + 5, w - m), m], fill="#D5DCE4")
            draw.line([x, h - m, min(x + 5, w - m), h - m], fill="#D5DCE4")
        for y in range(m, h - m, 12):
            draw.line([m, y, m, min(y + 5, h - m)], fill="#D5DCE4")
            draw.line([w - m, y, w - m, min(y + 5, h - m)], fill="#D5DCE4")

    for bc in layout.barcodes:
        symbol = _render_symbol(bc, max(8, bc.width), max(8, bc.height))
        img.paste(symbol, (bc.x, bc.y))

    for t in layout.texts:
        if t.mode == "graphic":
            glyphs = render_text_image(t.text, t.height)
        else:
            # Yazıcı fontu: yaklaşık görünüm, ama yazıcının kaplayacağı kutuya oturtulur
            glyphs = render_text_image(t.text, t.height).resize(
                (max(1, t.width), max(1, t.height)), Image.Resampling.LANCZOS
            )
        mask = glyphs.point(lambda p: 255 - p)
        img.paste(Image.new("RGB", glyphs.size, "black"), (t.x, t.y), mask)

    for ic in layout.icons:
        glyph = credit_icon(ic.height)
        img.paste(Image.new("RGB", glyph.size, "black"), (ic.x, ic.y), glyph.point(lambda p: 255 - p))

    for sh in layout.shapes:
        x1, y1 = sh.x + sh.width - 1, sh.y + sh.height - 1
        if sh.kind == "box":
            draw.rectangle([sh.x, sh.y, x1, y1], outline="black", width=sh.thickness)
        elif sh.kind == "bar":
            draw.rectangle([sh.x, sh.y, x1, y1], fill="black")
        elif sh.kind == "reverse":
            box = (sh.x, sh.y, min(w, sh.x + sh.width), min(h, sh.y + sh.height))
            img.paste(ImageOps.invert(img.crop(box)), box[:2])

    border = "#D93025" if layout.overflow else "#CCCCCC"
    draw.rectangle([0, 0, w - 1, h - 1], outline=border, width=4 if layout.overflow else 2)
    return img


def render_label_photoimage(
    label: LabelData,
    settings: LabelSettings,
    max_side: int = 320,
    max_size: tuple[int, int] | None = None,
) -> tuple[ImageTk.PhotoImage, Image.Image]:
    """Tkinter'da gösterilecek PhotoImage + ham PIL görüntüsü (alana sığdırılmış)."""
    base = render_label_image(label, settings)
    box_w, box_h = max_size or (max_side, max_side)
    ratio = min(box_w / base.width, box_h / base.height)
    if ratio != 1:
        base = base.resize(
            (max(1, int(base.width * ratio)), max(1, int(base.height * ratio))),
            Image.Resampling.LANCZOS,
        )
    return ImageTk.PhotoImage(base), base
