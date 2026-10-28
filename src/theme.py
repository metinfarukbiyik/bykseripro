"""
Kurumsal arayüz teması — yumuşak, yuvarlak köşeli, her platformda aynı.

ttk "clam" tabanı üzerine PIL ile çizilen görsel öğeler (9 dilimli
yuvarlak dikdörtgenler) kullanılır: düğmeler, giriş alanları, onay
kutuları, kartlar ve kaydırma çubukları Windows'ta da macOS havasında
görünür.

Stil adları:
  Page.TFrame / Page.TLabel     kart dışındaki zemin (alt çubuk vb.)
  Muted.TLabel                  ikincil açıklama metni
  CardTitle.TLabel / CardHead.TFrame   kart başlığı (kartın üstünde)
  Section.TLabel                kart içi bölüm başlığı
  TButton                       ikincil düğme (açık mavi-gri)
  Primary.TButton               ana eylem (mavi)
  Success.TButton               onaylayıcı eylem (yeşil)
  Warm.TButton                  dikkat çeken yardımcı eylem (amber)
  Header.TButton                lacivert başlık bandındaki düğmeler
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from PIL import Image, ImageDraw, ImageTk

# ── Palet ────────────────────────────────────────────────────────────
PAGE = "#EDF1F7"
CARD = "#FFFFFF"
CARD_BORDER = "#DCE3EE"
NAVY = "#1B3352"
NAVY_LIGHT = "#2A4970"
BLUE = "#2F6BDA"
BLUE_SOFT = "#DCE8FB"
GREEN = "#1F9D6B"
GOLD = "#C49A2C"
TEXT = "#1F2A37"
MUTED = "#6B7685"
FIELD_BORDER = "#C6D1E0"
FIELD_DISABLED = "#F2F4F8"
STRIPE = "#F7FAFE"

# Düğme varyantları: (dolgu üst, dolgu alt, kenar, yazı, hover üst, hover alt, basılı)
BUTTONS = {
    "TButton": ("#F4F7FC", "#E6ECF5", "#C9D4E4", NAVY, "#EAF1FB", "#DAE5F4", "#D3DEEE"),
    "Primary.TButton": ("#3B78E6", "#2A62CC", "#2557B8", "#FFFFFF", "#4683EE", "#3069D4", "#2252AA"),
    "Success.TButton": ("#27AE78", "#1C9262", "#178055", "#FFFFFF", "#2FBA82", "#1F9A69", "#16784F"),
    "Warm.TButton": ("#FFF4D9", "#FBE7B5", "#E8C877", "#6E4E00", "#FFF0CC", "#F8DFA0", "#F2D58C"),
    "Header.TButton": ("#2E4E77", "#25426A", "#3B5F8E", "#FFFFFF", "#365A86", "#2C4D78", "#223C61"),
}

_SS = 4  # süper örnekleme (yumuşak kenarlar)


def _hex(c: str, a: int = 255) -> tuple[int, int, int, int]:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), a


def _round_image(
    w: int,
    h: int,
    r: int,
    fill: str | tuple[str, str],
    border: str | None = None,
    bw: float = 1.0,
    shadow: int = 0,
    ring: str | None = None,
) -> Image.Image:
    """Yuvarlak dikdörtgen (RGBA). fill bir renk ya da (üst, alt) degrade."""
    S = _SS
    W, H = w * S, h * S
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    m = 2 * S if ring is not None else 0  # odak halkası için kenar payı
    bottom = H - 1 - shadow * S - m
    box = [m, m, W - 1 - m, bottom]
    rr = r * S

    if shadow:
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle(
            [box[0], box[1] + shadow * S, box[2], box[3] + shadow * S], rr, fill=_hex(NAVY, 28)
        )
        img = Image.alpha_composite(img, sh)
    if ring is not None:
        ImageDraw.Draw(img).rounded_rectangle([0, 0, W - 1, H - 1], rr + m, fill=_hex(ring, 150))

    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle(box, rr, fill=255)
    if isinstance(fill, tuple):
        top, bot = _hex(fill[0]), _hex(fill[1])
        grad = Image.new("RGBA", (W, H))
        gd = ImageDraw.Draw(grad)
        for y in range(H):
            t = y / max(1, H - 1)
            gd.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(4)))
        body = grad
    else:
        body = Image.new("RGBA", (W, H), _hex(fill))
    img.paste(body, (0, 0), mask)
    if border:
        ImageDraw.Draw(img).rounded_rectangle(box, rr, outline=_hex(border), width=max(1, int(bw * S)))
    return img.resize((w, h), Image.Resampling.LANCZOS)


def _chevron(w: int, h: int, color: str, up: bool = False, stroke: float = 1.7) -> Image.Image:
    """İnce, yuvarlak uçlu ok (⌄ / ⌃) — kutusuz; açılır liste ve sayı kutusu için."""
    S = _SS
    img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = w * S / 2, h * S / 2
    dx, dy = w * S * 0.2, h * S * 0.16
    if up:
        pts = [(cx - dx, cy + dy), (cx, cy - dy), (cx + dx, cy + dy)]
    else:
        pts = [(cx - dx, cy - dy), (cx, cy + dy), (cx + dx, cy - dy)]
    width = max(1, int(stroke * S))
    d.line(pts, fill=_hex(color), width=width, joint="curve")
    r = width / 2
    for x, y in (pts[0], pts[2]):  # yuvarlak uçlar
        d.ellipse([x - r, y - r, x + r, y + r], fill=_hex(color))
    return img.resize((w, h), Image.Resampling.LANCZOS)


def _check_image(size: int, on: bool, hover: bool, disabled: bool, radio: bool) -> Image.Image:
    S = _SS
    W = size * S
    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    box = [S, S, W - 1 - S, W - 1 - S]
    if disabled:
        fill, edge = FIELD_DISABLED, FIELD_BORDER
    elif on:
        fill, edge = BLUE, "#2557B8"
    else:
        fill, edge = CARD, BLUE if hover else "#AEBBCD"
    if radio:
        d.ellipse(box, fill=_hex(fill), outline=_hex(edge), width=int(1.2 * S))
        if on:
            c, rr = W / 2, W * 0.17
            d.ellipse([c - rr, c - rr, c + rr, c + rr], fill=_hex("#FFFFFF"))
    else:
        d.rounded_rectangle(box, 4 * S, fill=_hex(fill), outline=_hex(edge), width=int(1.2 * S))
        if on:
            pts = [(W * 0.27, W * 0.52), (W * 0.43, W * 0.68), (W * 0.74, W * 0.34)]
            d.line(pts, fill=_hex("#FFFFFF"), width=int(2.2 * S), joint="curve")
    return img.resize((size, size), Image.Resampling.LANCZOS)


def _parent_bg(parent: tk.Misc) -> str:
    """Bileşenin oturduğu zeminin rengi (tk ya da ttk kapsayıcı)."""
    try:
        if isinstance(parent, ttk.Widget):
            if parent.winfo_class() == "TLabelframe":
                return CARD  # kartın içi beyaz görsel
            name = str(parent.cget("style")) or parent.winfo_class()
            return ttk.Style(parent).lookup(name, "background") or CARD
        return str(parent.cget("bg"))
    except tk.TclError:
        return CARD


def button_style(parent: tk.Misc, base: str = "TButton") -> str:
    """
    Düğme görselleri yuvarlak köşelidir; köşelerde düğmenin arka planı görünür.
    Arka planı zeminle aynı olan türetilmiş stil döner (ör. lacivert bantta).
    """
    bg = _parent_bg(parent)
    style = ttk.Style(parent)
    if bg.lower() == str(style.lookup(base, "background")).lower():
        return base
    name = f"bg{bg.lstrip('#').upper()}.{base}"
    style.configure(name, background=bg)
    style.map(name, background=[("disabled", bg), ("pressed", bg), ("active", bg)])
    return name


def _bold(delta: int = 0) -> tkfont.Font:
    base = tkfont.nametofont("TkDefaultFont")
    f = base.copy()
    f.configure(weight="bold", size=base.cget("size") + delta)
    return f


def apply_theme(root: tk.Tk) -> None:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        return
    root.configure(bg=PAGE)

    images: list[ImageTk.PhotoImage] = []
    root._theme_images = images  # type: ignore[attr-defined]  # çöp toplanmasın
    fonts = {"title": _bold(), "heading": _bold()}
    root._theme_fonts = fonts  # type: ignore[attr-defined]

    def photo(img: Image.Image) -> ImageTk.PhotoImage:
        p = ImageTk.PhotoImage(img, master=root)
        images.append(p)
        return p

    style.configure(
        ".",
        background=CARD,
        foreground=TEXT,
        bordercolor=CARD_BORDER,
        lightcolor=CARD,
        darkcolor=CARD,
        troughcolor=PAGE,
        focuscolor=BLUE_SOFT,
        selectbackground=BLUE_SOFT,
        selectforeground=NAVY,
        insertcolor=BLUE,
    )
    style.map(".", foreground=[("disabled", "#9AA3AE")])

    # ── Zeminler ve metin ────────────────────────────────────────────
    style.configure("TFrame", background=CARD)
    style.configure("Page.TFrame", background=PAGE)
    style.configure("CardHead.TFrame", background=PAGE)
    style.configure("TLabel", background=CARD, foreground=TEXT)
    style.configure("Page.TLabel", background=PAGE, foreground=MUTED)
    style.configure("Muted.TLabel", background=CARD, foreground=MUTED)
    style.configure("CardTitle.TLabel", background=PAGE, foreground=NAVY, font=fonts["title"])
    style.configure("Section.TLabel", background=CARD, foreground=BLUE, font=fonts["title"])

    # ── Kart: yuvarlak, gölgeli; başlık kartın üstünde (macOS grup kutusu) ──
    card = photo(_round_image(40, 40, 10, CARD, CARD_BORDER, shadow=1))
    style.element_create("Card.border", "image", card, border=12, sticky="nsew")
    style.layout("TLabelframe", [("Card.border", {"sticky": "nsew"})])
    style.configure(
        "TLabelframe",
        background=PAGE,
        labeloutside=True,
        labelmargins=(4, 0, 0, 4),
        padding=(10, 6, 10, 8),
    )
    style.configure("TLabelframe.Label", background=PAGE, foreground=NAVY, font=fonts["title"])

    # ── Düğmeler ─────────────────────────────────────────────────────
    for name, (top, bot, edge, fg, htop, hbot, pressed) in BUTTONS.items():
        normal = photo(_round_image(32, 26, 7, (top, bot), edge, shadow=1))
        hover = photo(_round_image(32, 26, 7, (htop, hbot), edge, shadow=1))
        down = photo(_round_image(32, 26, 7, pressed, edge, shadow=1))
        off = photo(_round_image(32, 26, 7, FIELD_DISABLED, FIELD_BORDER, shadow=1))
        element = f"{name.replace('.', '_')}.border"
        style.element_create(
            element, "image", normal,
            ("disabled", off), ("pressed", down), ("active", hover),
            border=(9, 7, 9, 8), padding=(4, 1, 4, 2), sticky="nsew",
        )
        style.layout(name, [
            (element, {"sticky": "nsew", "children": [
                ("Button.padding", {"sticky": "nsew", "children": [
                    ("Button.label", {"sticky": "nsew"}),
                ]}),
            ]}),
        ])
        corner = NAVY if name == "Header.TButton" else CARD
        style.configure(name, foreground=fg, background=corner, padding=(8, 1), anchor="center")
        style.map(
            name,
            foreground=[("disabled", "#9AA3AE")],
            background=[("disabled", corner), ("pressed", corner), ("active", corner)],
        )

    # ── Giriş alanları (yuvarlak, odakta mavi halka) ─────────────────
    f_norm = photo(_round_image(30, 24, 6, CARD, FIELD_BORDER, ring=PAGE))
    f_hover = photo(_round_image(30, 24, 6, CARD, "#A9B8CC", ring=PAGE))
    f_focus = photo(_round_image(30, 24, 6, CARD, BLUE, bw=1.4, ring="#BFD3F7"))
    f_off = photo(_round_image(30, 24, 6, FIELD_DISABLED, FIELD_BORDER, ring=PAGE))
    style.element_create(
        "Soft.field", "image", f_norm,
        ("disabled", f_off), ("focus", f_focus), ("hover", f_hover),
        border=8, padding=(6, 1), sticky="nsew",
    )
    style.layout("TEntry", [
        ("Soft.field", {"sticky": "nsew", "children": [
            ("Entry.padding", {"sticky": "nsew", "children": [
                ("Entry.textarea", {"sticky": "nsew"}),
            ]}),
        ]}),
    ])
    # Oklar: clam'in kutulu üçgeni yerine ince chevron (Windows'ta da aynı)
    arrow_states = {
        name: (
            photo(_chevron(w, h, MUTED, up)),
            photo(_chevron(w, h, BLUE, up)),
            photo(_chevron(w, h, "#C3CBD6", up)),
        )
        for name, w, h, up in (
            ("down", 22, 16, False), ("spin_up", 16, 9, True), ("spin_down", 16, 9, False),
        )
    }
    for element, key in (
        ("Soft.downarrow", "down"),
        ("SoftSpin.uparrow", "spin_up"),
        ("SoftSpin.downarrow", "spin_down"),
    ):
        normal, hover, off = arrow_states[key]
        style.element_create(
            element, "image", normal,
            ("disabled", off), ("pressed", hover), ("active", hover), ("focus", hover),
            sticky="",
        )

    style.layout("TCombobox", [
        ("Soft.field", {"sticky": "nsew", "children": [
            ("Soft.downarrow", {"side": "right", "sticky": ""}),
            ("Combobox.padding", {"expand": "1", "sticky": "nsew", "children": [
                ("Combobox.textarea", {"sticky": "nsew"}),
            ]}),
        ]}),
    ])
    style.layout("TSpinbox", [
        ("Soft.field", {"sticky": "nsew", "children": [
            ("null", {"side": "right", "sticky": "", "children": [
                ("SoftSpin.uparrow", {"side": "top", "sticky": ""}),
                ("SoftSpin.downarrow", {"side": "bottom", "sticky": ""}),
            ]}),
            ("Spinbox.padding", {"sticky": "nsew", "children": [
                ("Spinbox.textarea", {"sticky": "nsew"}),
            ]}),
        ]}),
    ])
    for name in ("TEntry", "TCombobox", "TSpinbox"):
        style.configure(
            name, padding=(2, 0), fieldbackground=CARD, background=CARD,
            bordercolor=CARD, lightcolor=CARD, darkcolor=CARD,
        )
        style.map(name, fieldbackground=[("disabled", FIELD_DISABLED)])
    style.map(
        "TCombobox",
        fieldbackground=[("disabled", FIELD_DISABLED)],
        # salt okunur listede seçili metin mavi dolgu almasın
        selectbackground=[("readonly", CARD)],
        selectforeground=[("readonly", TEXT)],
    )
    root.option_add("*TCombobox*Listbox.background", CARD)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", BLUE)
    root.option_add("*TCombobox*Listbox.selectForeground", "#FFFFFF")
    root.option_add("*TCombobox*Listbox.borderWidth", 0)
    root.option_add("*TCombobox*Listbox.highlightThickness", 0)

    # ── Onay kutusu / seçenek ────────────────────────────────────────
    for radio, name in ((False, "TCheckbutton"), (True, "TRadiobutton")):
        st = {
            key: photo(_check_image(17, on, hover, off, radio))
            for key, on, hover, off in (
                ("off", False, False, False), ("hover", False, True, False),
                ("on", True, False, False), ("dis", False, False, True),
            )
        }
        element = f"Soft{'Radio' if radio else 'Check'}.indicator"
        style.element_create(
            element, "image", st["off"],
            ("disabled", st["dis"]), ("selected", st["on"]), ("active", st["hover"]),
            sticky="", padding=(0, 0, 8, 0),
        )
        base = name[1:]  # Checkbutton / Radiobutton
        style.layout(name, [
            (f"{base}.padding", {"sticky": "nsew", "children": [
                (element, {"side": "left", "sticky": ""}),
                (f"{base}.label", {"side": "left", "sticky": "nsew"}),
            ]}),
        ])
        style.configure(name, background=CARD, foreground=TEXT, padding=(2, 3))
        style.map(name, background=[("active", CARD)])

    # ── Tablo ────────────────────────────────────────────────────────
    style.configure(
        "Treeview", background=CARD, fieldbackground=CARD, foreground=TEXT,
        bordercolor=CARD_BORDER, lightcolor=CARD, darkcolor=CARD, rowheight=26,
    )
    style.map("Treeview", background=[("selected", BLUE_SOFT)], foreground=[("selected", NAVY)])
    style.configure(
        "Treeview.Heading", background="#F1F5FB", foreground=NAVY, font=fonts["heading"],
        relief="flat", bordercolor=CARD_BORDER, lightcolor="#F1F5FB", darkcolor="#F1F5FB",
        padding=(8, 5),
    )
    style.map("Treeview.Heading", background=[("active", BLUE_SOFT)])

    # ── Sekmeler ─────────────────────────────────────────────────────
    style.configure("TNotebook", background=CARD, bordercolor=CARD_BORDER, tabmargins=(0, 2, 0, 0))
    style.configure(
        "TNotebook.Tab", background="#EEF2F8", foreground=MUTED, bordercolor=CARD_BORDER,
        lightcolor="#EEF2F8", padding=(14, 4),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", CARD), ("active", "#E4EBF6")],
        foreground=[("selected", BLUE)],
        lightcolor=[("selected", CARD)],
    )

    # ── İnce, hap şeklinde kaydırma çubuğu (oksuz) ───────────────────
    thumb = photo(_round_image(10, 24, 4, "#C3CDDB"))
    thumb_h = photo(_round_image(10, 24, 4, "#9FAEC3"))
    style.element_create("Pill.thumb", "image", thumb, ("active", thumb_h), border=5, sticky="nsew")
    for orient, sticky in (("Vertical", "ns"), ("Horizontal", "ew")):
        style.layout(f"{orient}.TScrollbar", [
            (f"{orient}.Scrollbar.trough", {"sticky": sticky, "children": [
                ("Pill.thumb", {"expand": "1", "sticky": "nsew"}),
            ]}),
        ])
    style.configure("TScrollbar", troughcolor=CARD, bordercolor=CARD, width=10, arrowsize=10)
    style.configure("Page.Vertical.TScrollbar", troughcolor=PAGE, bordercolor=PAGE, background=PAGE)

    style.configure(
        "TProgressbar", background=BLUE, troughcolor="#E6ECF5", bordercolor="#E6ECF5",
        lightcolor=BLUE, darkcolor=BLUE,
    )
    style.configure("TSeparator", background=CARD_BORDER)
