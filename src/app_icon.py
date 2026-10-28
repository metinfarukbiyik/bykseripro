"""Uygulama pencere / görev çubuğu / dock ikonu.

Asset rolleri (assets/):
  app.png          — ana kimlik (kaynak). iconphoto / macOS / görev çubuğu
  app.ico          — Windows title bar, exe gömülü ikon, kısayollar
  app.icns         — macOS .app paket ikonu (BUILD_APP.sh / iconutil)
  app.iconset/     — app.icns üretim ara klasörü
  biyik_badge.png  — arayüz rozeti (splash / hakkinda / yardım); sistem ikonu değil
  whatsapp.png     — iletişim butonu; sistem ikonu değil

Yeniden üretim: python tools/prepare_icons.py
"""

from __future__ import annotations

import sys
import tkinter as tk

from PIL import Image, ImageTk

from paths import assets_dir

_PHOTO_CACHE: list[ImageTk.PhotoImage] = []
_APPLIED_ROOTS: set[int] = set()

# Title bar + görev çubuğu için birden fazla boyut (Tk en uygun olanı seçer)
_ICONPHOTO_SIZES = (16, 32, 48, 64)


def _absolute(path) -> str:
    return str(path.resolve())


def apply_app_icon(window: tk.Misc) -> None:
    """Pencere title bar / dock / görev çubuğu ikonunu ayarlar.

    PNG → iconphoto (çok boyutlu; Windows 10/11, macOS, modern Tk)
    ICO → iconbitmap (Windows klasik title bar / uyumluluk)
    """
    assets = assets_dir()
    png_path = assets / "app.png"
    ico_path = assets / "app.ico"

    # Aynı root'a tekrar tekrar yüklemeyi azalt
    try:
        root_id = id(window.winfo_toplevel())
    except Exception:
        root_id = id(window)

    photos: list[ImageTk.PhotoImage] = []
    try:
        src_path = png_path if png_path.exists() else ico_path
        if src_path.exists():
            base = Image.open(src_path).convert("RGBA")
            for side in _ICONPHOTO_SIZES:
                img = base.copy()
                img.thumbnail((side, side), Image.Resampling.LANCZOS)
                if img.size != (side, side):
                    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
                    canvas.paste(
                        img,
                        ((side - img.width) // 2, (side - img.height) // 2),
                        img,
                    )
                    img = canvas
                photo = ImageTk.PhotoImage(img)
                photos.append(photo)
                _PHOTO_CACHE.append(photo)
            if photos:
                # True → sonraki Toplevel pencereler aynı varsayılanı kullanır
                window.iconphoto(True, *photos)
    except Exception:
        pass

    # Windows: mutlak .ico yolu title bar için en güvenilir yol
    if sys.platform.startswith("win") and ico_path.exists():
        abs_ico = _absolute(ico_path)
        try:
            window.iconbitmap(default=abs_ico)
        except Exception:
            try:
                window.iconbitmap(abs_ico)
            except Exception:
                pass

    _APPLIED_ROOTS.add(root_id)
