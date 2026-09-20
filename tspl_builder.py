"""
TSPL etiket üretici — 98×98 mm kare etiket.

Şablon (yatay ortalı):
  [opsiyonel marka üstte]
  Ana barkod + metin
  (A-K barkod + metin)
  ItemNo / ParcaAd
  [opsiyonel marka altta]
"""

from __future__ import annotations

from dataclasses import dataclass

FONT_SIZE_PRESETS: dict[int, tuple[str, int, int]] = {
    1: ("2", 1, 1),  # Küçük   ~12×20
    2: ("3", 1, 1),  # Orta    ~16×24
    3: ("4", 1, 1),  # Büyük   ~24×32
    4: ("3", 2, 2),  # Çok büyük ~32×48
}

FONT_SIZE_LABELS = {
    1: "Küçük",
    2: "Orta",
    3: "Büyük",
    4: "Çok büyük",
}

BRAND_POSITIONS = {
    "top": "Üst",
    "bottom": "Alt",
}

# TSPL code type → arayüz etiketi
BARCODE_TYPES: dict[str, str] = {
    "128": "Code 128",
    "39": "Code 39",
    "93": "Code 93",
    "EAN13": "EAN-13",
    "EAN8": "EAN-8",
    "QRCODE": "QR Kod",
}


def normalize_barcode_type(raw: str | None, default: str = "128") -> str:
    key = (raw or default).strip().upper().replace(" ", "").replace("-", "")
    aliases = {
        "CODE128": "128",
        "CODE39": "39",
        "CODE93": "93",
        "QR": "QRCODE",
        "QRCODE": "QRCODE",
        "EAN13": "EAN13",
        "EAN8": "EAN8",
        "128": "128",
        "39": "39",
        "93": "93",
    }
    return aliases.get(key, default if default in BARCODE_TYPES else "128")


def dots_per_mm(dpi: int) -> float:
    return dpi / 25.4


FONT_METRICS = {
    "1": (8, 12),
    "2": (12, 20),
    "3": (16, 24),
    "4": (24, 32),
    "5": (32, 48),
    "0": (12, 20),
}


@dataclass
class LabelData:
    barkod: str
    ak_barkod: str = ""
    item_no: str = ""
    parca_ad: str = ""


@dataclass
class LabelSettings:
    width_mm: float = 98.0
    height_mm: float = 98.0
    gap_mm: float = 3.0
    dpi: int = 203
    copies: int = 1
    speed: int = 4
    density: int = 8
    direction: int = 1
    barcode_type: str = "128"
    ak_barcode_type: str = "128"
    barcode_height_mm: float = 20.0
    ak_barcode_height_mm: float = 14.0
    barcode_narrow: int = 3
    barcode_wide: int = 6
    qr_ecc: str = "M"  # L M Q H
    qr_cell: int = 4  # 1–10; 0 = otomatik sığdır
    # Ayrı font seviyeleri (1–4)
    font_barkod: int = 2
    font_ak: int = 2
    font_item: int = 3
    font_brand: int = 1
    # Markalama damgası
    brand_text: str = ""
    brand_position: str = "bottom"  # top | bottom
    gap_after_barcode_mm: float = 1.5
    gap_after_text_mm: float = 2.5
    gap_between_barcodes_mm: float = 4.0
    margin_mm: float = 6.0

    # Eski tek font alanı (geriye uyumluluk)
    @property
    def font_size(self) -> int:
        return int(self.font_item)


@dataclass
class LayoutBarcode:
    data: str
    x: int
    y: int
    width: int
    height: int
    narrow: int
    wide: int
    code_type: str = "128"
    kind: str = "linear"  # linear | qr
    cell: int = 4
    ecc: str = "M"


@dataclass
class LayoutText:
    text: str
    x: int
    y: int
    font: str
    x_mul: int
    y_mul: int
    width: int
    height: int
    kind: str = "content"  # content | brand


@dataclass
class LabelLayout:
    width: int
    height: int
    barcodes: list[LayoutBarcode]
    texts: list[LayoutText]


def _escape(text: str) -> str:
    return (text or "").replace('"', "'").strip()


def _norm(value: str | None) -> str:
    if value in (None, "", "None"):
        return ""
    return _escape(str(value))


def _clamp_font(size: int) -> int:
    return max(1, min(4, int(size)))


def _char_size(font: str, x_mul: int, y_mul: int) -> tuple[int, int]:
    w, h = FONT_METRICS.get(font, (16, 24))
    return w * x_mul, h * y_mul


def _text_width(text: str, font: str, x_mul: int) -> int:
    cw, _ = _char_size(font, x_mul, 1)
    return len(text) * cw


def _text_height(font: str, y_mul: int) -> int:
    _, ch = _char_size(font, 1, y_mul)
    return ch


def _code128_module_count(data: str) -> int:
    """Gerçek Code128 sembol genişliği (modül). Subset C sıkıştırmasını hesaba katar."""
    text = data or "0"
    try:
        from barcode.codex import Code128
        from barcode.writer import ImageWriter

        built = Code128(text, writer=ImageWriter()).build()
        if built and isinstance(built[0], str) and built[0]:
            return len(built[0])
    except Exception:
        pass
    # Yedek: her karakter 1 sembol varsayımı
    n = max(1, len(text))
    return 11 * (n + 2) + 13


def _approx_code128_width(data: str, narrow: int) -> int:
    """Yazıcıdaki Code128 çizgi genişliği (dot). Quiet zone dahil edilmez."""
    return _code128_module_count(data) * max(1, narrow)


def _fit_text_style(text: str, font_size: int, max_w: int) -> tuple[str, int, int, int]:
    size = _clamp_font(font_size)
    for level in range(size, 0, -1):
        font, xm, ym = FONT_SIZE_PRESETS[level]
        tw = _text_width(text, font, xm)
        if tw <= max_w:
            return font, xm, ym, tw
    for level in range(size, 0, -1):
        font, _, _ = FONT_SIZE_PRESETS[level]
        tw = _text_width(text, font, 1)
        if tw <= max_w:
            return font, 1, 1, tw
    return "1", 1, 1, _text_width(text, "1", 1)


def _approx_linear_width(data: str, code_type: str, narrow: int) -> int:
    narrow = max(1, narrow)
    t = normalize_barcode_type(code_type)
    n = max(1, len(data or "0"))
    if t == "128":
        return _approx_code128_width(data, narrow)
    if t == "39":
        return (n + 2) * 13 * narrow
    if t == "93":
        return (n + 2) * 9 * narrow
    if t == "EAN13":
        return 95 * narrow
    if t == "EAN8":
        return 67 * narrow
    return _approx_code128_width(data, narrow)


def _pick_narrow_wide(
    data: str, code_type: str, narrow: int, wide: int, max_w: int
) -> tuple[int, int, int]:
    narrow = max(1, min(6, narrow))
    wide = max(narrow + 1, wide)
    bc_w = _approx_linear_width(data, code_type, narrow)
    while bc_w > max_w and narrow > 1:
        narrow -= 1
        wide = max(narrow + 1, wide - 1)
        bc_w = _approx_linear_width(data, code_type, narrow)
    return narrow, wide, bc_w


def _qr_side_and_cell(
    desired_side: int, max_w: int, preferred_cell: int
) -> tuple[int, int]:
    """QR kare kenar (dot) ve hücre genişliği."""
    side = max(40, min(desired_side, max_w))
    # Tipik kısa veri ~25–33 modül; hücreyi kenara sığdır
    modules = 29
    if preferred_cell and preferred_cell > 0:
        cell = max(1, min(10, int(preferred_cell)))
    else:
        cell = max(1, min(10, side // modules))
    while cell * modules > max_w and cell > 1:
        cell -= 1
    return cell * modules, cell


def _center_x(page_w: int, content_w: int) -> int:
    """Sağ-sol tam ortalama."""
    return max(0, (page_w - content_w) // 2)


def _aligned_pair_x(page_w: int, bar_w: int, text_w: int) -> tuple[int, int]:
    """
    Barkod ve altındaki metni ortak merkeze hizalar.
    İkisi de sayfa ortasına göre yerleştirilir → birbirine ve kağıda ortalı.
    """
    center = page_w // 2
    bc_x = max(0, center - bar_w // 2)
    tx = max(0, center - text_w // 2)
    return bc_x, tx


def _make_text(
    text: str, y: int, page_w: int, max_w: int, font_size: int, kind: str = "content"
) -> LayoutText:
    font, xm, ym, tw = _fit_text_style(text, font_size, max_w)
    th = _text_height(font, ym)
    return LayoutText(
        text=text,
        x=_center_x(page_w, tw),
        y=y,
        font=font,
        x_mul=xm,
        y_mul=ym,
        width=tw,
        height=th,
        kind=kind,
    )


def compute_layout(label: LabelData, settings: LabelSettings) -> LabelLayout:
    dpm = dots_per_mm(settings.dpi)
    w = int(round(settings.width_mm * dpm))
    h = int(round(settings.height_mm * dpm))
    margin = int(round(settings.margin_mm * dpm))
    max_w = max(40, w - 2 * margin)

    barkod = _escape(str(label.barkod))
    ak = _norm(label.ak_barkod)
    item = _norm(label.item_no)
    parca = _norm(label.parca_ad)
    brand = _norm(settings.brand_text)
    brand_pos = (settings.brand_position or "bottom").lower()
    if brand_pos not in {"top", "bottom"}:
        brand_pos = "bottom"

    gap_after_bc = int(round(settings.gap_after_barcode_mm * dpm))
    gap_after_txt = int(round(settings.gap_after_text_mm * dpm))
    gap_bc = int(round(settings.gap_between_barcodes_mm * dpm))
    bc_h = int(round(settings.barcode_height_mm * dpm))
    ak_h = int(round(settings.ak_barcode_height_mm * dpm))

    main_type = normalize_barcode_type(settings.barcode_type)
    ak_type = normalize_barcode_type(
        getattr(settings, "ak_barcode_type", None) or settings.barcode_type
    )
    qr_ecc = (settings.qr_ecc or "M").upper()[:1]
    if qr_ecc not in {"L", "M", "Q", "H"}:
        qr_ecc = "M"
    qr_cell_pref = int(getattr(settings, "qr_cell", 4) or 0)

    font_barkod = _clamp_font(settings.font_barkod)
    font_ak = _clamp_font(settings.font_ak)
    font_item = _clamp_font(settings.font_item)
    font_brand = _clamp_font(settings.font_brand)

    main_n = main_w = 2
    main_bw = bc_h
    main_kind = "linear"
    main_cell = 4
    if main_type == "QRCODE":
        main_kind = "qr"
        main_bw, main_cell = _qr_side_and_cell(bc_h, max_w, qr_cell_pref)
        bc_h = main_bw  # kare
    else:
        main_n, main_w, main_bw = _pick_narrow_wide(
            barkod, main_type, settings.barcode_narrow, settings.barcode_wide, max_w
        )
    main_txt = _make_text(barkod, 0, w, max_w, font_barkod)

    ak_n = ak_w = ak_bw = 0
    ak_kind = "linear"
    ak_cell = 4
    ak_txt: LayoutText | None = None
    if ak:
        if ak_type == "QRCODE":
            ak_kind = "qr"
            ak_bw, ak_cell = _qr_side_and_cell(
                ak_h, max_w, max(1, qr_cell_pref - 1) if qr_cell_pref else 0
            )
            ak_h = ak_bw
            ak_n, ak_w = 1, 2
        else:
            ak_n, ak_w, ak_bw = _pick_narrow_wide(
                ak,
                ak_type,
                max(2, settings.barcode_narrow - 1),
                max(4, settings.barcode_wide - 2),
                max_w,
            )
        ak_txt = _make_text(ak, 0, w, max_w, font_ak)

    item_txt = _make_text(item, 0, w, max_w, font_item) if item else None
    parca_txt = _make_text(parca, 0, w, max_w, font_item) if parca else None
    brand_txt = (
        _make_text(brand, 0, w, max_w, font_brand, kind="brand") if brand else None
    )

    content_h = bc_h + gap_after_bc + main_txt.height
    if ak and ak_txt:
        content_h += gap_bc + ak_h + gap_after_bc + ak_txt.height
    if item_txt:
        content_h += gap_after_txt + item_txt.height
    if parca_txt:
        content_h += gap_after_txt + parca_txt.height

    brand_gap = int(round(2.0 * dpm))
    brand_block = (brand_txt.height + brand_gap) if brand_txt else 0

    # Marka için üst/alt rezerv; içerik kalan alanda dikey ortalanır
    top_reserve = margin + (brand_block if brand_txt and brand_pos == "top" else 0)
    bottom_reserve = margin + (brand_block if brand_txt and brand_pos == "bottom" else 0)
    usable = max(0, h - top_reserve - bottom_reserve)
    y = top_reserve + max(0, (usable - content_h) // 2)

    barcodes: list[LayoutBarcode] = []
    texts: list[LayoutText] = []

    if brand_txt and brand_pos == "top":
        texts.append(
            LayoutText(
                text=brand_txt.text,
                x=brand_txt.x,
                y=margin,
                font=brand_txt.font,
                x_mul=brand_txt.x_mul,
                y_mul=brand_txt.y_mul,
                width=brand_txt.width,
                height=brand_txt.height,
                kind="brand",
            )
        )

    # Ana barkod + metin — ortak merkez (kağıda ve birbirine ortalı)
    bc_x, tx = _aligned_pair_x(w, main_bw, main_txt.width)
    barcodes.append(
        LayoutBarcode(
            data=barkod,
            x=bc_x,
            y=y,
            width=main_bw,
            height=bc_h,
            narrow=main_n,
            wide=main_w,
            code_type=main_type,
            kind=main_kind,
            cell=main_cell,
            ecc=qr_ecc,
        )
    )
    y += bc_h + gap_after_bc
    texts.append(
        LayoutText(
            text=main_txt.text,
            x=tx,
            y=y,
            font=main_txt.font,
            x_mul=main_txt.x_mul,
            y_mul=main_txt.y_mul,
            width=main_txt.width,
            height=main_txt.height,
        )
    )
    y += main_txt.height

    if ak and ak_txt:
        y += gap_bc
        ak_x, ak_tx = _aligned_pair_x(w, ak_bw, ak_txt.width)
        barcodes.append(
            LayoutBarcode(
                data=ak,
                x=ak_x,
                y=y,
                width=ak_bw,
                height=ak_h,
                narrow=ak_n,
                wide=ak_w,
                code_type=ak_type,
                kind=ak_kind,
                cell=ak_cell,
                ecc=qr_ecc,
            )
        )
        y += ak_h + gap_after_bc
        texts.append(
            LayoutText(
                text=ak_txt.text,
                x=ak_tx,
                y=y,
                font=ak_txt.font,
                x_mul=ak_txt.x_mul,
                y_mul=ak_txt.y_mul,
                width=ak_txt.width,
                height=ak_txt.height,
            )
        )
        y += ak_txt.height

    if item_txt:
        y += gap_after_txt
        texts.append(
            LayoutText(
                text=item_txt.text,
                x=item_txt.x,
                y=y,
                font=item_txt.font,
                x_mul=item_txt.x_mul,
                y_mul=item_txt.y_mul,
                width=item_txt.width,
                height=item_txt.height,
            )
        )
        y += item_txt.height

    if parca_txt:
        y += gap_after_txt
        texts.append(
            LayoutText(
                text=parca_txt.text,
                x=parca_txt.x,
                y=y,
                font=parca_txt.font,
                x_mul=parca_txt.x_mul,
                y_mul=parca_txt.y_mul,
                width=parca_txt.width,
                height=parca_txt.height,
            )
        )

    if brand_txt and brand_pos == "bottom":
        texts.append(
            LayoutText(
                text=brand_txt.text,
                x=brand_txt.x,
                y=h - margin - brand_txt.height,
                font=brand_txt.font,
                x_mul=brand_txt.x_mul,
                y_mul=brand_txt.y_mul,
                width=brand_txt.width,
                height=brand_txt.height,
                kind="brand",
            )
        )

    return LabelLayout(width=w, height=h, barcodes=barcodes, texts=texts)


def build_tspl(label: LabelData, settings: LabelSettings) -> str:
    layout = compute_layout(label, settings)
    lines: list[str] = [
        f"SIZE {settings.width_mm:g} mm,{settings.height_mm:g} mm",
        f"GAP {settings.gap_mm:g} mm,0 mm",
        "CLS",
        f"DIRECTION {settings.direction}",
        f"SPEED {settings.speed}",
        f"DENSITY {settings.density}",
        "CODEPAGE UTF-8",
    ]

    for bc in layout.barcodes:
        if bc.kind == "qr" or normalize_barcode_type(bc.code_type) == "QRCODE":
            ecc = (bc.ecc or "M").upper()[:1]
            if ecc not in {"L", "M", "Q", "H"}:
                ecc = "M"
            cell = max(1, min(10, int(bc.cell or 4)))
            lines.append(
                f'QRCODE {bc.x},{bc.y},{ecc},{cell},A,0,M2,S7,"{bc.data}"'
            )
        else:
            ctype = normalize_barcode_type(bc.code_type or settings.barcode_type)
            lines.append(
                f'BARCODE {bc.x},{bc.y},"{ctype}",{bc.height},'
                f'0,0,{bc.narrow},{bc.wide},"{bc.data}"'
            )

    for t in layout.texts:
        lines.append(
            f'TEXT {t.x},{t.y},"{t.font}",0,{t.x_mul},{t.y_mul},"{t.text}"'
        )

    lines.append(f"PRINT {settings.copies},1")
    return "\r\n".join(lines) + "\r\n"


def build_batch_tspl(labels: list[LabelData], settings: LabelSettings) -> str:
    return "".join(build_tspl(label, settings) for label in labels)


def describe_layout(label: LabelData, settings: LabelSettings | None = None) -> str:
    s = settings or LabelSettings()
    main_t = normalize_barcode_type(s.barcode_type)
    ak_t = normalize_barcode_type(getattr(s, "ak_barcode_type", None) or s.barcode_type)
    rows = [
        f"Tip Ana:{BARCODE_TYPES.get(main_t, main_t)}  "
        f"2.barkod:{BARCODE_TYPES.get(ak_t, ak_t)}",
        f"Font Barkod:{s.font_barkod}  A-K:{s.font_ak}  Item:{s.font_item}",
        f"[BARKOD] {label.barkod}",
    ]
    if _norm(label.ak_barkod):
        rows.append(f"[A-K]    {label.ak_barkod}")
    if _norm(label.item_no):
        rows.append(f"[ItemNo] {label.item_no}")
    if _norm(label.parca_ad):
        rows.append(f"[Parça]  {label.parca_ad}")
    if _norm(s.brand_text):
        rows.append(f"[Marka]  {s.brand_text} ({s.brand_position})")
    return "\n".join(rows)
