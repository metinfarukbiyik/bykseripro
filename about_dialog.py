"""Kurumsal Hakkında penceresi — soft, net tasarım."""

from __future__ import annotations

import tkinter as tk
import webbrowser
from tkinter import ttk

from pathlib import Path

from PIL import Image, ImageTk

from paths import assets_dir
from app_icon import apply_app_icon
from ui_icons import C_NAVY as ICON_NAVY
from ui_icons import IconStore, icon_button, titled_label

ASSETS = assets_dir()

CONTACT_EMAIL = "metin@biyik.dev"
CONTACT_PHONE_DISPLAY = "+90 (540) 461 35 43"
CONTACT_PHONE_E164 = "905404613543"
WHATSAPP_URL = f"https://wa.me/{CONTACT_PHONE_E164}"
AUTHOR = "Metin Faruk BIYIK"

C_BG = "#F3F5F7"
C_CARD = "#FFFFFF"
C_LINE = "#E6E9EE"
C_TEXT = "#2A3340"
C_MUTED = "#6B7380"
C_NAVY = "#1B3352"
C_NAVY_SOFT = "#2A4566"
C_ACCENT = "#B8962E"
C_CHIP = "#F0F3F7"
C_WA_BG = "#EAF7EF"
C_WA_BG_HOVER = "#D8F0E2"
C_WA_TEXT = "#128C7E"


def _load_photo(path: Path, size: int, store: list) -> ImageTk.PhotoImage | None:
    if not path.exists():
        return None
    img = Image.open(path).convert("RGBA")
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    photo = ImageTk.PhotoImage(img)
    store.append(photo)
    return photo


def open_about(parent: tk.Tk | tk.Toplevel, app_title: str) -> None:
    """Modal Hakkında penceresi."""
    win = tk.Toplevel(parent)
    win.title("Hakkında")
    apply_app_icon(win)
    win.configure(bg=C_BG)
    win.resizable(False, False)
    win.transient(parent)
    win.grab_set()

    width, height = 500, 580
    win.geometry(f"{width}x{height}")
    win.update_idletasks()
    px = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
    py = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
    win.geometry(f"+{max(0, px)}+{max(0, py)}")

    photos: list[ImageTk.PhotoImage] = []
    icons = IconStore()

    # --- Soft üst alan: badge + uygulama adı ---
    header = tk.Frame(win, bg=C_CARD)
    header.pack(fill="x")

    head_inner = tk.Frame(header, bg=C_CARD)
    head_inner.pack(fill="x", padx=28, pady=22)

    badge = _load_photo(ASSETS / "biyik_badge.png", 72, photos)
    if badge:
        tk.Label(head_inner, image=badge, bg=C_CARD).pack(side="left", padx=(0, 16))

    titles = tk.Frame(head_inner, bg=C_CARD)
    titles.pack(side="left", fill="y")

    titled_label(
        titles,
        "Hakkında",
        "circle-info",
        icons,
        size=18,
        fill=C_NAVY,
        font=("Segoe UI Semibold", 16),
        bg=C_CARD,
        fg=C_NAVY,
    ).pack(anchor="w")
    tk.Label(
        titles,
        text=app_title,
        font=("Segoe UI", 10),
        fg=C_MUTED,
        bg=C_CARD,
        anchor="w",
    ).pack(anchor="w", pady=(4, 0))

    tk.Frame(header, bg=C_LINE, height=1).pack(fill="x")

    # --- İçerik ---
    body = tk.Frame(win, bg=C_BG)
    body.pack(fill="both", expand=True, padx=28, pady=20)

    # Tek akışlı metin — marka cümleyi bölmez
    tk.Label(
        body,
        text=(
            "Bu program; Excel üzerinden seri barkod etiketlerinin "
            "hızlı, hatasız ve tekrarlanabilir biçimde termal yazıcıya "
            "aktarılması ihtiyacı nedeniyle tasarlanıp kodlanmıştır."
        ),
        font=("Segoe UI", 10),
        fg=C_TEXT,
        bg=C_BG,
        wraplength=430,
        justify="left",
        anchor="w",
    ).pack(fill="x")

    # Soft kimlik satırı (badge zaten üstte; burada sade kredi)
    credit = tk.Frame(body, bg=C_CHIP)
    credit.pack(fill="x", pady=(14, 14))

    credit_inner = tk.Frame(credit, bg=C_CHIP)
    credit_inner.pack(fill="x", padx=14, pady=12)

    tk.Label(
        credit_inner,
        text="Tasarım & geliştirme",
        font=("Segoe UI", 8),
        fg=C_MUTED,
        bg=C_CHIP,
        anchor="w",
    ).pack(anchor="w")
    tk.Label(
        credit_inner,
        text=AUTHOR,
        font=("Segoe UI Semibold", 11),
        fg=C_NAVY,
        bg=C_CHIP,
        anchor="w",
    ).pack(anchor="w", pady=(2, 0))
    tk.Label(
        credit_inner,
        text="BIYIK.DEV",
        font=("Segoe UI", 9),
        fg=C_ACCENT,
        bg=C_CHIP,
        anchor="w",
    ).pack(anchor="w", pady=(1, 0))

    tk.Label(
        body,
        text=(
            "Amaç; üretim ve depo süreçlerinde tek tek kopyala-yapıştır "
            "baskı yükünü ortadan kaldırarak, şablonlu seri etiket "
            "baskısını tek tıkla yönetilebilir hale getirmektir."
        ),
        font=("Segoe UI", 9),
        fg=C_MUTED,
        bg=C_BG,
        wraplength=430,
        justify="left",
        anchor="w",
    ).pack(fill="x", pady=(0, 16))

    # Soft iletişim
    contact_title = tk.Frame(body, bg=C_BG)
    contact_title.pack(fill="x")
    titled_label(
        contact_title,
        "İletişim",
        "address-book",
        icons,
        size=14,
        fill=C_NAVY,
        font=("Segoe UI Semibold", 10),
        bg=C_BG,
        fg=C_NAVY,
    ).pack(anchor="w")
    tk.Frame(body, bg=C_ACCENT, height=2).pack(anchor="w", pady=(4, 10), ipadx=18)

    contact = tk.Frame(body, bg=C_CARD, highlightbackground=C_LINE, highlightthickness=1)
    contact.pack(fill="x", pady=(0, 14))

    contact_inner = tk.Frame(contact, bg=C_CARD)
    contact_inner.pack(fill="x", padx=14, pady=12)

    def _add_row(label: str, value: str, command, icon_name: str) -> None:
        row = tk.Frame(contact_inner, bg=C_CARD)
        row.pack(fill="x", pady=3)
        ic = icons.get(icon_name, size=12, fill=ICON_NAVY)
        if ic is not None:
            tk.Label(row, image=ic, bg=C_CARD).pack(side="left", padx=(0, 6))
        tk.Label(
            row,
            text=label,
            font=("Segoe UI", 8),
            fg=C_MUTED,
            bg=C_CARD,
            width=8,
            anchor="w",
        ).pack(side="left")
        link = tk.Label(
            row,
            text=value,
            font=("Segoe UI", 10),
            fg=C_NAVY_SOFT,
            bg=C_CARD,
            cursor="hand2",
            anchor="w",
        )
        link.pack(side="left")
        link.bind("<Button-1>", lambda _e: command())
        link.bind("<Enter>", lambda _e: link.configure(fg=C_ACCENT))
        link.bind("<Leave>", lambda _e: link.configure(fg=C_NAVY_SOFT))

    _add_row(
        "E-posta",
        CONTACT_EMAIL,
        lambda: webbrowser.open(f"mailto:{CONTACT_EMAIL}"),
        "envelope",
    )
    _add_row(
        "Telefon",
        CONTACT_PHONE_DISPLAY,
        lambda: webbrowser.open(f"tel:+{CONTACT_PHONE_E164}"),
        "phone",
    )

    # Soft WhatsApp butonu
    wa = tk.Frame(body, bg=C_WA_BG, cursor="hand2", highlightbackground="#C8E6D4", highlightthickness=1)
    wa.pack(fill="x")

    wa_inner = tk.Frame(wa, bg=C_WA_BG)
    wa_inner.pack(padx=12, pady=10)

    wa_icon = _load_photo(ASSETS / "whatsapp.png", 32, photos)
    if wa_icon:
        tk.Label(wa_inner, image=wa_icon, bg=C_WA_BG).pack(side="left", padx=(0, 10))

    tk.Label(
        wa_inner,
        text="WhatsApp üzerinden iletişime geçin",
        font=("Segoe UI Semibold", 10),
        fg=C_WA_TEXT,
        bg=C_WA_BG,
    ).pack(side="left")

    def _open_wa(_event=None) -> None:
        webbrowser.open(WHATSAPP_URL)

    def _paint(bg: str) -> None:
        wa.configure(bg=bg)
        wa_inner.configure(bg=bg)
        for child in wa_inner.winfo_children():
            try:
                child.configure(bg=bg)
            except tk.TclError:
                pass

    def _enter(_e=None) -> None:
        _paint(C_WA_BG_HOVER)

    def _leave(_e=None) -> None:
        _paint(C_WA_BG)

    for widget in (wa, wa_inner, *wa_inner.winfo_children()):
        widget.bind("<Button-1>", _open_wa)
        widget.bind("<Enter>", _enter)
        widget.bind("<Leave>", _leave)

    # Footer
    footer = tk.Frame(win, bg=C_BG)
    footer.pack(fill="x", padx=28, pady=(0, 16))
    tk.Label(
        footer,
        text="© BIYIK.DEV",
        font=("Segoe UI", 8),
        fg=C_MUTED,
        bg=C_BG,
    ).pack(side="left")
    icon_button(
        footer, "Kapat", "circle-xmark", win.destroy, icons, fill=C_MUTED
    ).pack(side="right")

    win._photos = photos  # type: ignore[attr-defined]
    win._icons = icons  # type: ignore[attr-defined]
    win.bind("<Escape>", lambda _e: win.destroy())
    win.focus_set()
