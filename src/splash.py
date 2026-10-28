"""Soft kurumsal açılış ekranı."""

from __future__ import annotations

import tkinter as tk

from PIL import Image, ImageTk

from paths import assets_dir
from app_icon import apply_app_icon
from ui_icons import C_MUTED as ICON_MUTED
from ui_icons import C_NAVY as ICON_NAVY
from ui_icons import IconStore

ASSETS = assets_dir()

C_BG = "#F3F5F7"
C_CARD = "#FFFFFF"
C_NAVY = "#1B3352"
C_GOLD = "#B8962E"
C_MUTED = "#6B7380"
C_LINE = "#E6E9EE"


def show_splash(duration_ms: int = 2400) -> None:
    """Logo ve renkli başlık ile soft açılış penceresi gösterir."""
    win = tk.Tk()
    win.title("BIYIK.DEV")
    apply_app_icon(win)
    win.configure(bg=C_BG)
    win.overrideredirect(True)
    win.attributes("-topmost", True)

    width, height = 460, 300
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    win.geometry(f"{width}x{height}+{(sw - width) // 2}+{(sh - height) // 2}")

    photos: list[ImageTk.PhotoImage] = []
    icons = IconStore()

    card = tk.Frame(
        win,
        bg=C_CARD,
        highlightbackground=C_LINE,
        highlightthickness=1,
    )
    card.pack(fill="both", expand=True, padx=14, pady=14)

    inner = tk.Frame(card, bg=C_CARD)
    inner.pack(expand=True)

    badge_path = ASSETS / "biyik_badge.png"
    if badge_path.exists():
        img = Image.open(badge_path).convert("RGBA")
        img = img.resize((88, 88), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        photos.append(photo)
        tk.Label(inner, image=photo, bg=C_CARD).pack(pady=(8, 14))

    title_row = tk.Frame(inner, bg=C_CARD)
    title_row.pack()
    barcode_ic = icons.get("barcode", size=16, fill=ICON_NAVY)
    if barcode_ic is not None:
        tk.Label(title_row, image=barcode_ic, bg=C_CARD).pack(side="left", padx=(0, 6))
    tk.Label(
        title_row,
        text="BYK Seri Baskı Pro",
        font=("Segoe UI Semibold", 13),
        fg=C_NAVY,
        bg=C_CARD,
    ).pack(side="left")

    tk.Label(
        inner,
        text="Biyik.dev",
        font=("Segoe UI Semibold", 16),
        fg=C_GOLD,
        bg=C_CARD,
    ).pack(pady=(4, 10))

    tk.Frame(inner, bg=C_GOLD, height=2).pack(fill="x", padx=80, pady=(0, 10))

    tk.Label(
        inner,
        text="Kurumsal etiket baskı çözümü",
        font=("Segoe UI", 9),
        fg=C_MUTED,
        bg=C_CARD,
    ).pack()

    load_row = tk.Frame(inner, bg=C_CARD)
    load_row.pack(pady=(16, 4))
    spin_ic = icons.get("arrows-rotate", size=12, fill=ICON_MUTED)
    if spin_ic is not None:
        tk.Label(load_row, image=spin_ic, bg=C_CARD).pack(side="left", padx=(0, 6))
    tk.Label(
        load_row,
        text="Yükleniyor…",
        font=("Segoe UI", 8),
        fg=C_MUTED,
        bg=C_CARD,
    ).pack(side="left")

    win._photos = photos  # type: ignore[attr-defined]
    win._icons = icons  # type: ignore[attr-defined]

    def _close() -> None:
        win.destroy()

    win.after(duration_ms, _close)
    win.bind("<Button-1>", lambda _e: _close())
    win.bind("<Escape>", lambda _e: _close())
    win.mainloop()
