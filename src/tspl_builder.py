"""
TSPL etiket üretici — her boyutta etiket (98×98, 100×40 …).

Şablon (yatay ortalı):
  [opsiyonel marka üstte]
  Ana barkod + metin          | 2. barkod yan yana da konabilir
  (2. barkod + metin)
  ItemNo / ParcaAd            (uzun metin satırlara bölünür, her satır ortalı)
  [opsiyonel marka altta]

Etikete sığmayan içerik "otomatik sığdır" ile boşluk / barkod yüksekliği /
font küçültülerek yerleştirilir.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from branding import LABEL_CREDIT

from text_render import (
    credit_icon,
    graphic_text_width,
    render_text_image,
    truncate_to_width,
    tspl_bitmap_payload,
    wrap_text,
)

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

BRAND_STYLES = {
    "plain": "Düz",
    "box": "Çerçeveli",
    "inverse": "Ters (siyah bant)",
    "lines": "Üst-alt çizgili",
}

# Elle taşınabilen öğe grupları → arayüz adı
ELEMENT_GROUPS = {
    "main": "Ana barkod",
    "ak": "2. barkod",
    "item": "Orta metin",
    "parca": "Alt metin",
    "brand": "Marka",
}
ALIGNMENTS = {"left": "Sol", "center": "Orta", "right": "Sağ"}
VALIGNS = {"top": "Üst", "center": "Orta", "bottom": "Alt"}

AK_POSITIONS = {
    "below": "Alt alta",
    "side": "Yan yana",
}

TEXT_MODES = {
    "graphic": "Grafik (Türkçe karakter, tam ortalı)",
    "printer": "Yazıcı fontu",
}

# Grafik modda font seviyesi → satır yüksekliği (dot); yazıcı fontlarıyla eş boy
GRAPHIC_LINE_HEIGHTS = {1: 20, 2: 24, 3: 32, 4: 48}

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


# Yazıcı dahili fontlarının karakter boyutu (nokta) — TSPL kılavuzu.
# Aynı font 300 DPI yazıcıda daha çok nokta kaplar; yanlış tablo metni kaydırır.
FONT_METRICS = {
    "1": (8, 12),
    "2": (12, 20),
    "3": (16, 24),
    "4": (24, 32),
    "5": (32, 48),
    "0": (12, 20),
}
FONT_METRICS_300 = {
    "1": (12, 20),
    "2": (16, 28),
    "3": (24, 32),
    "4": (32, 48),
    "5": (48, 64),
    "0": (16, 28),
}


def _font_metrics(font: str, dpi: int) -> tuple[int, int]:
    if dpi >= 550:  # 600 DPI: 300 DPI ölçülerinin iki katı
        w, h = FONT_METRICS_300.get(font, (24, 32))
        return w * 2, h * 2
    if dpi >= 250:
        return FONT_METRICS_300.get(font, (24, 32))
    return FONT_METRICS.get(font, (16, 24))


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
    brand_enabled: bool = True
    brand_text: str = ""
    brand_position: str = "bottom"  # top | bottom
    brand_style: str = "plain"  # plain | box | inverse | lines
    gap_after_barcode_mm: float = 1.5
    gap_after_text_mm: float = 2.5
    gap_between_barcodes_mm: float = 4.0
    margin_mm: float = 6.0
    # Yerleşim (önizleme panelinden yönetilir)
    show_main_text: bool = True
    show_ak: bool = True
    show_ak_text: bool = True
    show_item: bool = True
    show_parca: bool = True
    ak_position: str = "below"  # below | side
    auto_fit: bool = True
    max_text_lines: int = 2  # uzun metin en fazla kaç satıra bölünsün
    text_mode: str = "graphic"  # graphic | printer
    offset_x_mm: float = 0.0  # yazıcı kalibrasyonu (+ sağa)
    offset_y_mm: float = 0.0  # (+ aşağı)
    # Öğe bazında ince ayar (Yerleşim penceresi)
    font_parca: int = 0  # 0 = orta metinle aynı
    ak_barcode_narrow: int = 0  # 0 = otomatik (ana çizgi kalınlığına göre)
    content_valign: str = "center"  # top | center | bottom
    element_align: dict = field(default_factory=dict)  # grup → left | center | right
    element_offsets: dict = field(default_factory=dict)  # grup → [dx_mm, dy_mm]

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
    group: str = ""


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
    kind: str = "content"  # content | brand | credit
    mode: str = "printer"  # printer (TEXT) | graphic (BITMAP)
    group: str = ""


@dataclass
class LayoutShape:
    """Marka tasarımı için şekil: box (çerçeve) | bar (dolu) | reverse (ters çevir)."""

    kind: str
    x: int
    y: int
    width: int
    height: int
    thickness: int = 2
    group: str = ""


@dataclass
class LayoutIcon:
    """Program imzası ikonu (BITMAP olarak basılır)."""

    x: int
    y: int
    width: int
    height: int
    group: str = "credit"


@dataclass
class LabelLayout:
    width: int
    height: int
    barcodes: list[LayoutBarcode]
    texts: list[LayoutText]
    overflow: bool = False
    fit_note: str = ""
    margin: int = 0
    shapes: list[LayoutShape] = field(default_factory=list)
    icons: list[LayoutIcon] = field(default_factory=list)
    # Önizlemede seçim/sürükleme için grup kutuları (nokta): grup → (x0, y0, x1, y1)
    group_boxes: dict = field(default_factory=dict)
    out_of_bounds: list = field(default_factory=list)  # etiket dışına taşan gruplar


def _escape(text: str) -> str:
    return (text or "").replace('"', "'").strip()


def _norm(value: str | None) -> str:
    if value in (None, "", "None"):
        return ""
    return _escape(str(value))


def _clamp_font(size: int) -> int:
    return max(1, min(4, int(size)))


def _char_size(font: str, x_mul: int, y_mul: int, dpi: int = 203) -> tuple[int, int]:
    w, h = _font_metrics(font, dpi)
    return w * x_mul, h * y_mul


def _text_width(text: str, font: str, x_mul: int, dpi: int = 203) -> int:
    cw, _ = _char_size(font, x_mul, 1, dpi)
    return len(text) * cw


def _text_height(font: str, y_mul: int, dpi: int = 203) -> int:
    _, ch = _char_size(font, 1, y_mul, dpi)
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




# ── Metin blokları ───────────────────────────────────────────────────


def _graphic_h(dots_at_203: int, dpi: int) -> int:
    """Grafik metin yüksekliği — 300 DPI yazıcıda da aynı fiziksel boy."""
    return max(8, int(round(dots_at_203 * dpi / 203)))


def _text_styles(level: int, mode: str, dpi: int = 203) -> list[tuple[str, int, int, int]]:
    """Büyükten küçüğe aday stiller: (font, x_mul, y_mul, satır_yüksekliği)."""
    level = _clamp_font(level)
    styles: list[tuple[str, int, int, int]] = []
    if mode == "graphic":
        for lv in range(level, 0, -1):
            styles.append(("G", 1, 1, _graphic_h(GRAPHIC_LINE_HEIGHTS[lv], dpi)))
        styles.append(("G", 1, 1, _graphic_h(16, dpi)))
        return styles
    for lv in range(level, 0, -1):
        font, xm, ym = FONT_SIZE_PRESETS[lv]
        styles.append((font, xm, ym, _text_height(font, ym, dpi)))
    styles.append(("1", 1, 1, _text_height("1", 1, dpi)))
    return styles


def _measurer(mode: str, font: str, x_mul: int, line_h: int, dpi: int = 203):
    if mode == "graphic":
        return lambda t: graphic_text_width(t, line_h)
    return lambda t: _text_width(t, font, x_mul, dpi)


def _text_block(
    text: str,
    max_w: int,
    level: int,
    mode: str,
    max_lines: int,
    kind: str = "content",
    dpi: int = 203,
) -> tuple[list[LayoutText], int]:
    """
    Metni max_w içine sığdırır: önce aynı fontta satırlara böler, olmazsa
    fontu küçültür; en küçük fontta da sığmazsa son satırı '...' ile kısaltır.
    Döner: (y'si bloğa göreli satırlar, blok yüksekliği). x sonra atanır.
    """
    max_lines = max(1, int(max_lines))
    styles = _text_styles(level, mode, dpi)
    chosen = None
    for font, xm, ym, lh in styles:
        measure = _measurer(mode, font, xm, lh, dpi)
        lines = wrap_text(text, max_w, measure, max_lines)
        if lines is not None:
            chosen = (font, xm, ym, lh, measure, lines)
            break
    if chosen is None:
        font, xm, ym, lh = styles[-1]
        measure = _measurer(mode, font, xm, lh, dpi)
        lines = wrap_text(text, max_w, measure, 999) or [text]
        if len(lines) > max_lines:
            rest = " ".join(lines[max_lines - 1 :])
            lines = lines[: max_lines - 1] + [rest]
        lines[-1] = truncate_to_width(lines[-1], max_w, measure)
        chosen = (font, xm, ym, lh, measure, lines)

    font, xm, ym, lh, measure, lines = chosen
    line_gap = max(2, lh // 6)
    out: list[LayoutText] = []
    y = 0
    for i, line in enumerate(lines):
        if i:
            y += line_gap
        out.append(
            LayoutText(
                text=line,
                x=0,
                y=y,
                font=font,
                x_mul=xm,
                y_mul=ym,
                width=measure(line),
                height=lh,
                kind=kind,
                mode=mode,
            )
        )
        y += lh
    return out, y


def _credit_line(
    max_w: int, mode: str, dpi: int
) -> tuple[LayoutText, LayoutIcon, int, int]:
    """
    Program imzası — [ikon] BYK Seri Baskı Pro · biyik.dev (tek satır).
    Döner: (metin, ikon, satır yüksekliği, toplam genişlik); x'ler satır başına göreli.
    """
    if mode == "graphic":
        th = _graphic_h(16, dpi)
        measure = _measurer(mode, "G", 1, th)
        font = "G"
    else:
        font = "2"
        th = _text_height(font, 1, dpi)
        measure = _measurer(mode, font, 1, th, dpi)
    ih = _graphic_h(22, dpi)
    iw = credit_icon(ih).width
    gap = max(3, ih // 4)
    text = truncate_to_width(LABEL_CREDIT, max(0, max_w - iw - gap), measure)
    line_h = max(ih, th)
    icon = LayoutIcon(x=0, y=(line_h - ih) // 2, width=iw, height=ih)
    line = LayoutText(
        text=text, x=iw + gap, y=(line_h - th) // 2, font=font, x_mul=1, y_mul=1,
        width=measure(text), height=th, kind="credit", mode=mode,
    )
    return line, icon, line_h, iw + gap + line.width


def _brand_block(
    text: str, max_w: int, level: int, mode: str, max_lines: int, style: str, dpm: float
) -> tuple[list[LayoutText], list[LayoutShape], int]:
    """
    Marka metni + tasarım şekilleri. x'ler merkeze göre sonra atanır
    (şekillerde x = -genişlik/2 göreli tutulur), y'ler bloğa göreli.
    """
    framed = style in {"box", "inverse", "lines"}
    pad_y = int(round(1.0 * dpm)) if framed else 0
    pad_x = int(round(2.0 * dpm)) if style == "box" else 0
    thick = max(2, int(round(0.3 * dpm)))
    lines, text_h = _text_block(
        text, max(40, max_w - 2 * pad_x - 2 * thick), level, mode, max_lines,
        kind="brand", dpi=int(round(dpm * 25.4)),
    )
    for t in lines:
        t.y += pad_y
    block_h = text_h + 2 * pad_y
    shapes: list[LayoutShape] = []
    if style == "box":
        bw = min(max_w, max(t.width for t in lines) + 2 * pad_x)
        shapes.append(LayoutShape("box", -(bw // 2), 0, bw, block_h, thick))
    elif style == "inverse":
        shapes.append(LayoutShape("reverse", -(max_w // 2), 0, max_w, block_h))
    elif style == "lines":
        shapes.append(LayoutShape("bar", -(max_w // 2), 0, max_w, thick))
        shapes.append(LayoutShape("bar", -(max_w // 2), block_h - thick, max_w, thick))
    return lines, shapes, block_h


def _place_centered(
    lines: list[LayoutText], shapes: list[LayoutShape], cx: int, y0: int,
    out_tx: list, out_sh: list,
) -> None:
    for t in lines:
        t.x = max(0, cx - t.width // 2)
        t.y += y0
        out_tx.append(t)
    for sh in shapes:
        sh.x = max(0, cx + sh.x)
        sh.y += y0
        out_sh.append(sh)


# ── Yerleşim ─────────────────────────────────────────────────────────


@dataclass
class _Column:
    """Dikey sıralı öğeler; y'ler sütun başına göreli, x sütun merkezine göre atanır."""

    barcodes: list[LayoutBarcode]
    texts: list[LayoutText]
    height: int = 0
    too_wide: bool = False

    def place(self, center_x: int, y0: int, out_bc: list, out_tx: list) -> None:
        for bc in self.barcodes:
            bc.x = max(0, center_x - bc.width // 2)
            bc.y += y0
            out_bc.append(bc)
        for t in self.texts:
            t.x = max(0, center_x - t.width // 2)
            t.y += y0
            out_tx.append(t)


def _barcode_column(
    data: str,
    code_type: str,
    height: int,
    narrow: int,
    wide: int,
    qr_cell: int,
    qr_ecc: str,
    max_w: int,
    text_level: int,
    show_text: bool,
    gap_after_bc: int,
    mode: str,
    max_lines: int,
    dpi: int = 203,
) -> _Column:
    col = _Column(barcodes=[], texts=[])
    if code_type == "QRCODE":
        # Yükseklik alanı QR kare kenarıdır
        side, cell = _qr_side_and_cell(height, min(max_w, height), qr_cell)
        bc = LayoutBarcode(
            data=data, x=0, y=0, width=side, height=side, narrow=1, wide=2,
            code_type=code_type, kind="qr", cell=cell, ecc=qr_ecc,
        )
    else:
        n, wd, bw = _pick_narrow_wide(data, code_type, narrow, wide, max_w)
        col.too_wide = bw > max_w
        bc = LayoutBarcode(
            data=data, x=0, y=0, width=bw, height=height, narrow=n, wide=wd,
            code_type=code_type,
        )
    col.barcodes.append(bc)
    col.height = bc.height
    if show_text:
        lines, block_h = _text_block(data, max_w, text_level, mode, max_lines, dpi=dpi)
        for t in lines:
            t.y += col.height + gap_after_bc
        col.texts.extend(lines)
        col.height += gap_after_bc + block_h
    return col


# Otomatik sığdırma adımları: (boşluk katsayısı, barkod yük. katsayısı, font düşüşü)
_FIT_STEPS: tuple[tuple[float, float, int], ...] = (
    (1.0, 1.0, 0),
    (0.6, 1.0, 0),
    (0.5, 0.85, 0),
    (0.4, 0.7, 0),
    (0.35, 0.55, 0),
    (0.35, 0.55, 1),
    (0.3, 0.45, 1),
    (0.25, 0.4, 2),
)


def compute_layout(label: LabelData, settings: LabelSettings) -> LabelLayout:
    s = settings
    dpm = dots_per_mm(s.dpi)
    w = int(round(s.width_mm * dpm))
    h = int(round(s.height_mm * dpm))
    margin = int(round(max(0.0, s.margin_mm) * dpm))
    max_w = max(40, w - 2 * margin)
    mode = s.text_mode if s.text_mode in TEXT_MODES else "graphic"
    max_lines = max(1, min(4, int(s.max_text_lines or 1)))

    barkod = _escape(str(label.barkod))
    ak = _norm(label.ak_barkod) if s.show_ak else ""
    item = _norm(label.item_no) if s.show_item else ""
    parca = _norm(label.parca_ad) if s.show_parca else ""
    brand = _norm(s.brand_text) if s.brand_enabled else ""
    brand_style = s.brand_style if s.brand_style in BRAND_STYLES else "plain"
    brand_pos = (s.brand_position or "bottom").lower()
    if brand_pos not in BRAND_POSITIONS:
        brand_pos = "bottom"
    side_by_side = bool(ak) and s.ak_position == "side"

    main_type = normalize_barcode_type(s.barcode_type)
    ak_type = normalize_barcode_type(
        getattr(s, "ak_barcode_type", None) or s.barcode_type
    )
    qr_ecc = (s.qr_ecc or "M").upper()[:1]
    if qr_ecc not in {"L", "M", "Q", "H"}:
        qr_ecc = "M"
    qr_cell_pref = int(getattr(s, "qr_cell", 4) or 0)

    # Program imzası (her zaman en üstte) + marka (kenara sabit, sığdırmadan etkilenmez)
    credit_text, credit_ic, credit_h, credit_w = _credit_line(max_w, mode, s.dpi)
    credit_block = credit_h + int(round(1.0 * dpm))
    brand_lines: list[LayoutText] = []
    brand_shapes: list[LayoutShape] = []
    brand_h = 0
    if brand:
        brand_lines, brand_shapes, brand_h = _brand_block(
            brand, max_w, s.font_brand, mode, max_lines, brand_style, dpm
        )
    brand_block = brand_h + int(round(2.0 * dpm)) if brand_lines else 0
    top_reserve = margin + credit_block + (brand_block if brand_pos == "top" else 0)
    bottom_reserve = margin + (brand_block if brand_pos == "bottom" else 0)
    usable = max(0, h - top_reserve - bottom_reserve)
    min_bc = int(round(4.0 * dpm))

    steps = _FIT_STEPS if s.auto_fit else _FIT_STEPS[:1]
    plan = None
    for gap_k, bc_k, drop in steps:
        gap_after_bc = int(round(s.gap_after_barcode_mm * dpm * gap_k))
        gap_after_txt = int(round(s.gap_after_text_mm * dpm * gap_k))
        gap_bc = int(round(s.gap_between_barcodes_mm * dpm * gap_k))
        # Küçültme 4 mm altına inmez (kullanıcı zaten daha kısa seçtiyse o kalır)
        bc_user = s.barcode_height_mm * dpm
        ak_user = s.ak_barcode_height_mm * dpm
        bc_h = int(round(max(min(min_bc, bc_user), bc_user * bc_k)))
        ak_h = int(round(max(min(min_bc, ak_user), ak_user * bc_k)))

        def lv(level: int) -> int:
            return max(1, _clamp_font(level) - drop)

        col_w = max_w
        col_gap = max(gap_bc, int(round(2.0 * dpm)))
        if side_by_side:
            col_w = max(40, (max_w - col_gap) // 2)

        main_col = _barcode_column(
            barkod, main_type, bc_h, s.barcode_narrow, s.barcode_wide,
            qr_cell_pref, qr_ecc, col_w, lv(s.font_barkod), s.show_main_text,
            gap_after_bc, mode, max_lines, s.dpi,
        )
        ak_col = None
        if ak:
            ak_narrow = int(s.ak_barcode_narrow or 0) or max(2, s.barcode_narrow - 1)
            ak_col = _barcode_column(
                ak, ak_type, ak_h,
                ak_narrow, max(ak_narrow + 1, ak_narrow * 2),
                max(1, qr_cell_pref - 1) if qr_cell_pref else 0, qr_ecc,
                col_w, lv(s.font_ak), s.show_ak_text, gap_after_bc, mode, max_lines,
                s.dpi,
            )

        extra: list[tuple[str, list[LayoutText], int]] = []
        for group, txt, level in (
            ("item", item, s.font_item),
            ("parca", parca, int(s.font_parca or 0) or s.font_item),
        ):
            if txt:
                lines, block_h = _text_block(txt, max_w, lv(level), mode, max_lines, dpi=s.dpi)
                extra.append((group, lines, block_h))

        if ak_col and side_by_side:
            top_h = max(main_col.height, ak_col.height)
        elif ak_col:
            top_h = main_col.height + gap_bc + ak_col.height
        else:
            top_h = main_col.height
        content_h = top_h + sum(gap_after_txt + bh for _, _, bh in extra)

        plan = (gap_k, bc_k, drop, gap_bc, gap_after_txt, col_w, col_gap,
                main_col, ak_col, extra, top_h, content_h)
        if content_h <= usable:
            break

    assert plan is not None
    (gap_k, bc_k, drop, gap_bc, gap_after_txt, col_w, col_gap,
     main_col, ak_col, extra, top_h, content_h) = plan
    overflow = content_h > usable

    barcodes: list[LayoutBarcode] = []
    texts: list[LayoutText] = []
    shapes: list[LayoutShape] = []
    cx = w // 2
    free = max(0, usable - content_h)
    valign = s.content_valign if s.content_valign in VALIGNS else "center"
    y = top_reserve + {"top": 0, "center": free // 2, "bottom": free}[valign]

    icons: list[LayoutIcon] = []
    credit_x = max(0, cx - credit_w // 2)
    for obj in (credit_text, credit_ic):
        obj.x += credit_x
        obj.y += margin
    texts.append(credit_text)
    icons.append(credit_ic)
    if brand_lines and brand_pos == "top":
        _place_centered(brand_lines, brand_shapes, cx, margin + credit_block, texts, shapes)

    if ak_col and side_by_side:
        off = (col_w + col_gap) // 2
        # Sütunlar kendi içinde dikey ortalı
        main_col.place(cx - off, y + (top_h - main_col.height) // 2, barcodes, texts)
        ak_col.place(cx + off, y + (top_h - ak_col.height) // 2, barcodes, texts)
    else:
        main_col.place(cx, y, barcodes, texts)
        if ak_col:
            ak_col.place(cx, y + main_col.height + gap_bc, barcodes, texts)
    y += top_h

    for group, lines, block_h in extra:
        y += gap_after_txt
        for t in lines:
            t.x = max(0, cx - t.width // 2)
            t.y += y
            t.group = group
            texts.append(t)
        y += block_h

    if brand_lines and brand_pos == "bottom":
        _place_centered(brand_lines, brand_shapes, cx, h - margin - brand_h, texts, shapes)

    # Grupları işaretle (sütunlar ve marka yerleştirildikten sonra)
    for bc in main_col.barcodes:
        bc.group = "main"
    for t in main_col.texts:
        t.group = "main"
    if ak_col:
        for obj in (*ak_col.barcodes, *ak_col.texts):
            obj.group = "ak"
    for obj in (*brand_lines, *brand_shapes):
        obj.group = "brand"
    credit_text.group = "credit"

    _apply_element_tweaks(s, dpm, w, margin, barcodes, texts, shapes)
    out_of_bounds = [
        g for g, (x0, y0, x1, y1) in _group_boxes(barcodes, texts, shapes, icons).items()
        if g in ELEMENT_GROUPS and (x0 < 0 or y0 < 0 or x1 > w or y1 > h)
    ]
    for obj in (*barcodes, *texts, *shapes):
        obj.x, obj.y = max(0, obj.x), max(0, obj.y)  # yazıcı negatif koordinat almaz

    # Yazıcı kalibrasyon kaydırması
    ox = int(round(s.offset_x_mm * dpm))
    oy = int(round(s.offset_y_mm * dpm))
    if ox or oy:
        for obj in (*barcodes, *texts, *shapes, *icons):
            obj.x = max(0, obj.x + ox)
            obj.y = max(0, obj.y + oy)

    notes: list[str] = []
    if (gap_k, bc_k, drop) != (1.0, 1.0, 0):
        notes.append(
            f"Otomatik sığdırıldı: barkod %{round(bc_k * 100)}, "
            f"boşluk %{round(gap_k * 100)}"
            + (f", font −{drop}" if drop else "")
        )
    if overflow:
        notes.append(
            "Etikete sığmıyor: 2. barkodu 'Yan yana' alın, barkod yüksekliğini, "
            "kenar boşluğunu azaltın ya da bazı alanları gizleyin."
        )
    if main_col.too_wide or (ak_col is not None and ak_col.too_wide):
        notes.append("Barkod verisi çok uzun; genişliğe sığmıyor.")
    if out_of_bounds:
        names = ", ".join(ELEMENT_GROUPS[g] for g in out_of_bounds)
        notes.append(f"Etiket dışına taşan: {names}. Konumunu ya da boyutunu düzeltin.")

    return LabelLayout(
        width=w,
        height=h,
        barcodes=barcodes,
        texts=texts,
        overflow=(
            overflow or main_col.too_wide or bool(ak_col and ak_col.too_wide)
            or bool(out_of_bounds)
        ),
        fit_note="\n".join(notes),
        margin=margin,
        shapes=shapes,
        icons=icons,
        group_boxes=_group_boxes(barcodes, texts, shapes, icons),
        out_of_bounds=out_of_bounds,
    )


def _group_boxes(barcodes, texts, shapes, icons) -> dict[str, tuple[int, int, int, int]]:
    boxes: dict[str, list[int]] = {}
    for obj in (*barcodes, *texts, *shapes, *icons):
        if not obj.group:
            continue
        b = boxes.setdefault(obj.group, [obj.x, obj.y, obj.x + obj.width, obj.y + obj.height])
        b[0], b[1] = min(b[0], obj.x), min(b[1], obj.y)
        b[2], b[3] = max(b[2], obj.x + obj.width), max(b[3], obj.y + obj.height)
    return {g: tuple(b) for g, b in boxes.items()}


def _apply_element_tweaks(s: LabelSettings, dpm: float, w: int, margin: int,
                          barcodes, texts, shapes) -> None:
    """Öğe bazında hizalama (sol/orta/sağ) ve elle kaydırma (mm)."""
    align = s.element_align or {}
    offsets = s.element_offsets or {}
    left, right = margin, w - margin
    for group in ELEMENT_GROUPS:
        g_bc = [b for b in barcodes if b.group == group]
        g_tx = [t for t in texts if t.group == group]
        g_sh = [sh for sh in shapes if sh.group == group]
        if not (g_bc or g_tx or g_sh):
            continue
        mode = align.get(group, "center")
        box = next((sh for sh in g_sh if sh.kind == "box"), None)
        if mode in ("left", "right"):
            if group in ("main", "ak") or box is not None:
                # Barkod bloğu ya da çerçeveli marka: hepsi birlikte, dış kenara göre
                # Barkod bloğu (barkod + metni) birlikte kayar
                objs = [*g_bc, *g_tx, *([box] if box is not None else [])]
                x0 = min(o.x for o in objs)
                x1 = max(o.x + o.width for o in objs)
                dx = left - x0 if mode == "left" else right - x1
                for o in objs:
                    o.x += dx
            else:
                # Metin satırları tek tek hizalanır
                for t in g_tx:
                    t.x = left if mode == "left" else right - t.width
        dx_mm, dy_mm = (list(offsets.get(group) or [0, 0]) + [0, 0])[:2]
        dx, dy = int(round(float(dx_mm) * dpm)), int(round(float(dy_mm) * dpm))
        if dx or dy:
            for o in (*g_bc, *g_tx, *g_sh):
                o.x += dx
                o.y += dy


# ── TSPL çıktısı ─────────────────────────────────────────────────────


def _command_parts(
    label: LabelData, settings: LabelSettings
) -> list[str | tuple[str, bytes, str]]:
    """Komut satırları; BITMAP satırları (başlık, ikili veri, açıklama) olarak döner."""
    layout = compute_layout(label, settings)
    parts: list[str | tuple[str, bytes, str]] = [
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
            parts.append(f'QRCODE {bc.x},{bc.y},{ecc},{cell},A,0,M2,S7,"{bc.data}"')
        else:
            ctype = normalize_barcode_type(bc.code_type or settings.barcode_type)
            parts.append(
                f'BARCODE {bc.x},{bc.y},"{ctype}",{bc.height},'
                f'0,0,{bc.narrow},{bc.wide},"{bc.data}"'
            )

    for ic in layout.icons:
        wb, hh, data = tspl_bitmap_payload(credit_icon(ic.height))
        parts.append((f"BITMAP {ic.x},{ic.y},{wb},{hh},0,", data, "imza ikonu"))

    for t in layout.texts:
        if t.mode == "graphic":
            img = render_text_image(t.text, t.height)
            wb, hh, data = tspl_bitmap_payload(img)
            parts.append((f"BITMAP {t.x},{t.y},{wb},{hh},0,", data, t.text))
        else:
            parts.append(
                f'TEXT {t.x},{t.y},"{t.font}",0,{t.x_mul},{t.y_mul},"{t.text}"'
            )

    # Şekiller metinden sonra: REVERSE altındaki yazıyı beyaza çevirir
    for sh in layout.shapes:
        if sh.kind == "box":
            parts.append(
                f"BOX {sh.x},{sh.y},{sh.x + sh.width},{sh.y + sh.height},{sh.thickness}"
            )
        elif sh.kind == "bar":
            parts.append(f"BAR {sh.x},{sh.y},{sh.width},{sh.height}")
        elif sh.kind == "reverse":
            parts.append(f"REVERSE {sh.x},{sh.y},{sh.width},{sh.height}")

    parts.append(f"PRINT {settings.copies},1")
    return parts


def build_tspl(label: LabelData, settings: LabelSettings) -> str:
    """Okunabilir TSPL (önizleme sekmesi). BITMAP verisi özetlenir."""
    lines: list[str] = []
    for part in _command_parts(label, settings):
        if isinstance(part, tuple):
            head, data, text = part
            lines.append(f'{head}<{len(data)} bayt: "{text}">')
        else:
            lines.append(part)
    return "\r\n".join(lines) + "\r\n"


def build_tspl_bytes(label: LabelData, settings: LabelSettings) -> bytes:
    """Yazıcıya gidecek ham TSPL."""
    out = bytearray()
    for part in _command_parts(label, settings):
        if isinstance(part, tuple):
            head, data, _ = part
            out += head.encode("ascii") + data
        else:
            out += part.encode("utf-8", errors="replace")
        out += b"\r\n"
    return bytes(out)


def build_batch_tspl(labels: list[LabelData], settings: LabelSettings) -> bytes:
    return b"".join(build_tspl_bytes(label, settings) for label in labels)


def describe_layout(label: LabelData, settings: LabelSettings | None = None) -> str:
    s = settings or LabelSettings()
    main_t = normalize_barcode_type(s.barcode_type)
    ak_t = normalize_barcode_type(getattr(s, "ak_barcode_type", None) or s.barcode_type)
    rows = [
        f"Tip Ana:{BARCODE_TYPES.get(main_t, main_t)}  "
        f"2.barkod:{BARCODE_TYPES.get(ak_t, ak_t)}",
        f"Font Barkod:{s.font_barkod}  2.Barkod:{s.font_ak}  Metin:{s.font_item}",
        f"Metin: {TEXT_MODES.get(s.text_mode, s.text_mode)}  ·  "
        f"2. barkod: {AK_POSITIONS.get(s.ak_position, s.ak_position)}",
        f"[BARKOD] {label.barkod}",
    ]
    if _norm(label.ak_barkod):
        rows.append(f"[2.Bark] {label.ak_barkod}")
    if _norm(label.item_no):
        rows.append(f"[Orta]   {label.item_no}")
    if _norm(label.parca_ad):
        rows.append(f"[Alt]    {label.parca_ad}")
    rows.append(f"[İmza]   {LABEL_CREDIT}")
    if s.brand_enabled and _norm(s.brand_text):
        rows.append(
            f"[Marka]  {s.brand_text} ({s.brand_position}, "
            f"{BRAND_STYLES.get(s.brand_style, s.brand_style)})"
        )
    note = compute_layout(label, s).fit_note
    if note:
        rows.append(f"[Not]    {note}")
    return "\n".join(rows)
