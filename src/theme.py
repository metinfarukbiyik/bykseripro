"""
Kurumsal arayüz teması — ttk "clam" tabanı, her platformda aynı görünüm.

Gri sayfa zemini üzerinde beyaz kartlar (LabelFrame), lacivert vurgu,
altın ikincil renk. Tüm ttk bileşenleri (düğme, giriş, açılır liste,
onay kutusu, tablo, sekme, kaydırma çubuğu) burada tanımlanır.

Stil adları:
  Page.TFrame / Page.TLabel   kart dışındaki alanlar (alt çubuk vb.)
  Muted.TLabel                ikincil açıklama metni
  CardTitle.TLabel            kart başlığı
  Primary.TButton             öne çıkan eylem (baskı)
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

PAGE = "#EEF1F5"
CARD = "#FFFFFF"
NAVY = "#1B3352"
NAVY_HOVER = "#27466E"
NAVY_SOFT = "#DCE6F3"
GOLD = "#B8962E"
TEXT = "#1F2A37"
MUTED = "#6B7380"
BORDER = "#D5DCE5"
BORDER_STRONG = "#A9B5C4"
FIELD_DISABLED = "#F3F5F8"
HOVER = "#F2F5F9"
STRIPE = "#F7F9FC"


def _bold(size_delta: int = 0) -> tkfont.Font:
    base = tkfont.nametofont("TkDefaultFont")
    f = base.copy()
    f.configure(weight="bold", size=base.cget("size") + size_delta)
    return f


def apply_theme(root: tk.Tk) -> None:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        return
    root.configure(bg=PAGE)
    # Font nesneleri kökte tutulur (çöp toplanmasın)
    root._theme_fonts = {"title": _bold(), "heading": _bold()}  # type: ignore[attr-defined]
    fonts = root._theme_fonts  # type: ignore[attr-defined]

    style.configure(
        ".",
        background=CARD,
        foreground=TEXT,
        bordercolor=BORDER,
        lightcolor=CARD,
        darkcolor=CARD,
        troughcolor=PAGE,
        focuscolor=NAVY_SOFT,
        selectbackground=NAVY_SOFT,
        selectforeground=NAVY,
        insertcolor=NAVY,
    )
    style.map(".", foreground=[("disabled", "#9AA3AE")])

    # Zeminler
    style.configure("TFrame", background=CARD)
    style.configure("Page.TFrame", background=PAGE)
    style.configure("TLabel", background=CARD, foreground=TEXT)
    style.configure("Page.TLabel", background=PAGE, foreground=MUTED)
    style.configure("Muted.TLabel", background=CARD, foreground=MUTED)
    style.configure("CardTitle.TLabel", background=CARD, foreground=NAVY, font=fonts["title"])
    style.configure("Section.TLabel", background=CARD, foreground=GOLD, font=fonts["title"])

    # Kartlar
    style.configure(
        "TLabelframe",
        background=CARD,
        bordercolor=BORDER,
        lightcolor=CARD,
        darkcolor=CARD,
        relief="solid",
        borderwidth=1,
        padding=(10, 6, 10, 8),
    )
    style.configure("TLabelframe.Label", background=CARD, foreground=NAVY, font=fonts["title"])

    # Düğmeler
    style.configure(
        "TButton",
        background=CARD,
        foreground=NAVY,
        bordercolor=BORDER_STRONG,
        lightcolor=CARD,
        darkcolor=CARD,
        focuscolor=CARD,
        padding=(10, 4),
        relief="flat",
    )
    style.map(
        "TButton",
        background=[("disabled", FIELD_DISABLED), ("pressed", NAVY_SOFT), ("active", HOVER)],
        bordercolor=[("active", NAVY), ("focus", NAVY)],
        lightcolor=[("pressed", NAVY_SOFT), ("active", HOVER)],
        darkcolor=[("pressed", NAVY_SOFT), ("active", HOVER)],
    )
    style.configure(
        "Primary.TButton",
        background=NAVY,
        foreground="#FFFFFF",
        bordercolor=NAVY,
        lightcolor=NAVY,
        darkcolor=NAVY,
        focuscolor=NAVY,
    )
    style.map(
        "Primary.TButton",
        background=[("disabled", "#8C9BB0"), ("pressed", NAVY), ("active", NAVY_HOVER)],
        foreground=[("disabled", "#E6EAF0")],
        lightcolor=[("active", NAVY_HOVER)],
        darkcolor=[("active", NAVY_HOVER)],
        bordercolor=[("active", NAVY_HOVER)],
    )

    # Giriş alanları
    field = {
        "fieldbackground": CARD,
        "bordercolor": BORDER_STRONG,
        "lightcolor": CARD,
        "darkcolor": CARD,
        "padding": (6, 2),
    }
    field_map = {
        "fieldbackground": [("disabled", FIELD_DISABLED), ("readonly", CARD)],
        "bordercolor": [("focus", NAVY), ("active", NAVY)],
        "lightcolor": [("focus", NAVY_SOFT)],
    }
    style.configure("TEntry", **field)
    style.map("TEntry", **field_map)
    style.configure("TSpinbox", arrowcolor=NAVY, arrowsize=11, background=CARD, **field)
    style.map("TSpinbox", **field_map)
    style.configure("TCombobox", arrowcolor=NAVY, arrowsize=12, background=CARD, **field)
    style.map(
        "TCombobox",
        **field_map,
        background=[("active", HOVER)],
        # salt okunur listede seçili metin mavi dolgu almasın
        selectbackground=[("readonly", CARD), ("focus", NAVY_SOFT)],
        selectforeground=[("readonly", TEXT), ("focus", NAVY)],
    )
    root.option_add("*TCombobox*Listbox.background", CARD)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", NAVY)
    root.option_add("*TCombobox*Listbox.selectForeground", "#FFFFFF")
    root.option_add("*TCombobox*Listbox.borderWidth", 0)

    # Onay kutusu / seçenek düğmesi
    for name in ("TCheckbutton", "TRadiobutton"):
        style.configure(
            name,
            background=CARD,
            foreground=TEXT,
            indicatorbackground=CARD,
            indicatorforeground="#FFFFFF",
            indicatormargin=(0, 0, 8, 0),
            upperbordercolor=BORDER_STRONG,
            lowerbordercolor=BORDER_STRONG,
            focuscolor=CARD,
            padding=(2, 3),
        )
        style.map(
            name,
            background=[("active", CARD)],
            indicatorbackground=[
                ("disabled", FIELD_DISABLED),
                ("selected", NAVY),
                ("active", HOVER),
            ],
            upperbordercolor=[("selected", NAVY), ("active", NAVY)],
            lowerbordercolor=[("selected", NAVY), ("active", NAVY)],
        )

    # Tablo
    style.configure(
        "Treeview",
        background=CARD,
        fieldbackground=CARD,
        foreground=TEXT,
        bordercolor=BORDER,
        rowheight=26,
    )
    style.map(
        "Treeview",
        background=[("selected", NAVY_SOFT)],
        foreground=[("selected", NAVY)],
    )
    style.configure(
        "Treeview.Heading",
        background=PAGE,
        foreground=NAVY,
        font=fonts["heading"],
        relief="flat",
        bordercolor=BORDER,
        lightcolor=PAGE,
        darkcolor=PAGE,
        padding=(8, 5),
    )
    style.map("Treeview.Heading", background=[("active", NAVY_SOFT)])

    # Sekmeler
    style.configure("TNotebook", background=CARD, bordercolor=BORDER, tabmargins=(0, 4, 0, 0))
    style.configure(
        "TNotebook.Tab",
        background=PAGE,
        foreground=MUTED,
        bordercolor=BORDER,
        lightcolor=PAGE,
        padding=(14, 4),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", CARD), ("active", HOVER)],
        foreground=[("selected", NAVY)],
        lightcolor=[("selected", CARD)],
    )

    # Kaydırma çubuğu / ilerleme
    style.configure(
        "TScrollbar",
        background="#D9E0E8",
        troughcolor=PAGE,
        bordercolor=PAGE,
        lightcolor="#D9E0E8",
        darkcolor="#D9E0E8",
        arrowcolor=MUTED,
        gripcount=0,
    )
    style.map("TScrollbar", background=[("active", BORDER_STRONG)])
    style.configure(
        "TProgressbar",
        background=NAVY,
        troughcolor=PAGE,
        bordercolor=BORDER,
        lightcolor=NAVY,
        darkcolor=NAVY,
    )
    style.configure("TSeparator", background=BORDER)
