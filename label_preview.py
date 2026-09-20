"""Etiket görsel önizlemesi (Pillow + Code128/39/93/EAN + QR)."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw, ImageFont, ImageTk

from tspl_builder import LabelData, LabelSettings, LayoutBarcode, compute_layout, normalize_barcode_type


def _load_font(size: int) -> ImageFont.ImageFont:
    for name in ("arialbd.ttf", "arial.ttf", "Arial.ttf", "segoeui.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, max(8, size))
        except OSError:
            continue
    return ImageFont.load_default()


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


def render_label_image(
    label: LabelData,
    settings: LabelSettings,
    scale: float = 0.55,
) -> Image.Image:
    """Etiket yerleşimini görsel olarak çizer — TSPL layout ile aynı koordinatlar."""
    layout = compute_layout(label, settings)
    w = max(1, int(layout.width * scale))
    h = max(1, int(layout.height * scale))
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, w - 1, h - 1], outline="#CCCCCC", width=2)

    for bc in layout.barcodes:
        bw = max(8, int(bc.width * scale))
        bh = max(8, int(bc.height * scale))
        bx = int(round((w - bw) / 2))
        by = int(bc.y * scale)
        barcode_img = _render_symbol(bc, bw, bh)
        img.paste(barcode_img, (bx, by))

    for t in layout.texts:
        px = max(10, int(t.height * scale * 0.95))
        font = _load_font(px)
        bbox = draw.textbbox((0, 0), t.text, font=font)
        tw = bbox[2] - bbox[0]
        tx = max(0, (w - tw) // 2)
        ty = int(t.y * scale)
        fill = "#666666" if getattr(t, "kind", "") == "brand" else "black"
        draw.text((tx, ty), t.text, fill=fill, font=font)

    return img


def render_label_photoimage(
    label: LabelData,
    settings: LabelSettings,
    max_side: int = 320,
) -> tuple[ImageTk.PhotoImage, Image.Image]:
    """Tkinter'da gösterilecek PhotoImage + ham PIL görüntüsü."""
    base = render_label_image(label, settings, scale=0.55)
    side = max(base.width, base.height)
    if side > max_side:
        ratio = max_side / side
        base = base.resize(
            (max(1, int(base.width * ratio)), max(1, int(base.height * ratio))),
            Image.Resampling.LANCZOS,
        )
    return ImageTk.PhotoImage(base), base
