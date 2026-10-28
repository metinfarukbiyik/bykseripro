"""Font Awesome ikonları — ctkfontawesome + Pillow (Cairo gerekmez)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ctkfontawesome import icon_to_image
from PIL.ImageTk import PhotoImage

# Kurumsal palet
C_NAVY = "#1B3352"
C_GOLD = "#B8962E"
C_MUTED = "#6B7380"
C_GREEN = "#2E7D4F"
C_TEAL = "#1F6B5C"
C_BLUE = "#2A5A8C"
C_WARN = "#8A6A1A"


class IconStore:
    """PhotoImage referanslarını tutar (GC önleme) ve ikon üretir."""

    def __init__(self) -> None:
        self._refs: list[PhotoImage] = []

    def get(
        self,
        name: str,
        *,
        size: int = 14,
        fill: str = C_NAVY,
    ) -> PhotoImage | None:
        try:
            img = icon_to_image(name, fill=fill, scale_to_width=size)
        except Exception:
            return None
        self._refs.append(img)
        return img

    def keep(self, img: PhotoImage | None) -> PhotoImage | None:
        if img is not None:
            self._refs.append(img)
        return img


def icon_button(
    parent: tk.Misc,
    text: str,
    icon: str,
    command,
    store: IconStore,
    *,
    size: int = 14,
    fill: str = C_NAVY,
    **kwargs,
) -> ttk.Button:
    """İkon + metin içeren ttk.Button."""
    img = store.get(icon, size=size, fill=fill)
    opts: dict = {"text": f" {text}", "command": command, **kwargs}
    if img is not None:
        opts["image"] = img
        opts["compound"] = "left"
    return ttk.Button(parent, **opts)


def icon_labelframe(
    parent: tk.Misc,
    text: str,
    icon: str,
    store: IconStore,
    *,
    size: int = 13,
    fill: str = C_NAVY,
    padding: int = 4,
) -> ttk.LabelFrame:
    """Solunda Font Awesome ikonu olan LabelFrame."""
    frame = ttk.LabelFrame(parent, padding=padding)
    label = ttk.Frame(frame)
    img = store.get(icon, size=size, fill=fill)
    if img is not None:
        ttk.Label(label, image=img).pack(side="left", padx=(0, 6))
    title_lbl = ttk.Label(label, text=text)
    title_lbl.pack(side="left")
    frame.configure(labelwidget=label)
    frame.title_label = title_lbl  # type: ignore[attr-defined]
    return frame


def titled_label(
    parent: tk.Misc,
    text: str,
    icon: str,
    store: IconStore,
    *,
    size: int = 16,
    fill: str = C_NAVY,
    font: tuple = ("Segoe UI Semibold", 15),
    bg: str | None = None,
    fg: str = C_NAVY,
) -> tk.Frame:
    """Başlık satırı: ikon + metin."""
    row = tk.Frame(parent, bg=bg) if bg else ttk.Frame(parent)
    img = store.get(icon, size=size, fill=fill)
    if img is not None:
        kw = {"image": img}
        if bg:
            kw["bg"] = bg
        tk.Label(row, **kw).pack(side="left", padx=(0, 8))
    lbl_kw: dict = {"text": text, "font": font, "fg": fg, "anchor": "w"}
    if bg:
        lbl_kw["bg"] = bg
    tk.Label(row, **lbl_kw).pack(side="left")
    return row


# Barkod çizgi deseni (göreli genişlik, boşluk) — marka işareti için
_MARK_BARS = (2, 1, 1, 1, 3, 1, 1, 2, 2, 1, 1, 1, 3)


def app_mark(parent: tk.Misc, size: int = 36, bg: str = "#FFFFFF") -> tk.Canvas:
    """
    Uygulamanın vektör marka işareti: lacivert yuvarlak karo, beyaz barkod
    çizgileri ve altın etiket şeridi. Canvas ile çizilir → her ölçekte keskin.
    """
    c = tk.Canvas(parent, width=size, height=size, bg=bg, highlightthickness=0)
    r = size * 0.24
    s = size - 1
    # Yuvarlak köşeli karo (smooth poligon)
    pts = [
        r, 0, s - r, 0, s, 0, s, r, s, s - r, s, s, s - r, s,
        r, s, 0, s, 0, s - r, 0, r, 0, 0,
    ]
    c.create_polygon(pts, smooth=True, fill=C_NAVY, outline=C_NAVY)

    # Barkod çizgileri
    left, right = size * 0.22, size * 0.78
    top, bottom = size * 0.22, size * 0.64
    total = sum(_MARK_BARS)
    unit = (right - left) / total
    x = left
    for i, w in enumerate(_MARK_BARS):
        if i % 2 == 0:  # çift indeks = çizgi, tek = boşluk
            c.create_rectangle(x, top, x + w * unit, bottom, fill="#FFFFFF", width=0)
        x += w * unit

    # Altın etiket şeridi
    c.create_rectangle(
        left, size * 0.72, right, size * 0.78, fill=C_GOLD, width=0
    )
    return c
