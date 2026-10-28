"""Güncelleme bildirimi — yeni sürümü gösterir, indirir ve kurar."""

from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk
from typing import Callable

from branding import APP_DISPLAY, PRODUCT_PAGE, PRODUCT_PAGE_LABEL
from paths import assets_dir
from ui_icons import C_GOLD, C_MUTED, C_NAVY, IconStore
from updater import (
    ReleaseInfo,
    current_version,
    install_update,
    release_highlights,
    self_update_blocker,
)

C_BG = "#FFFFFF"
C_SOFT = "#F5F7FA"
C_LINE = "#E6E9EE"
C_HEAD_SUB = "#C9D3E0"
C_PRIMARY = "#1B3352"
C_PRIMARY_HOVER = "#27466E"
C_NOTICE_BG = "#FFF8E6"
C_NOTICE_FG = "#6B5414"


class _Button(tk.Label):
    """Platformdan bağımsız renkli düğme (macOS'ta tk.Button arka planı boyanmaz)."""

    def __init__(self, parent, text: str, command, primary: bool = False) -> None:
        self._primary = primary
        self._bg = C_PRIMARY if primary else C_BG
        self._hover = C_PRIMARY_HOVER if primary else C_SOFT
        super().__init__(
            parent,
            text=text,
            font=("Segoe UI Semibold", 10),
            fg="#FFFFFF" if primary else C_NAVY,
            bg=self._bg,
            padx=18,
            pady=8,
            cursor="hand2",
            highlightthickness=0 if primary else 1,
            highlightbackground=C_LINE,
        )
        self._command = command
        self._enabled = True
        self.bind("<Button-1>", lambda _e: self._enabled and self._command())
        self.bind("<Enter>", lambda _e: self._enabled and self.configure(bg=self._hover))
        self.bind("<Leave>", lambda _e: self.configure(bg=self._bg if self._enabled else C_SOFT))

    def set_enabled(self, on: bool) -> None:
        self._enabled = on
        if on:
            self.configure(
                bg=self._bg, fg="#FFFFFF" if self._primary else C_NAVY, cursor="hand2"
            )
        else:
            self.configure(bg=C_SOFT, fg="#A0A7B2", cursor="arrow")


def _link(parent, text: str, command, *, size: int = 9, fg: str = C_NAVY) -> tk.Label:
    lbl = tk.Label(
        parent, text=text, font=("Segoe UI", size, "underline"), fg=fg, bg=C_BG,
        cursor="hand2",
    )
    lbl.bind("<Button-1>", lambda _e: command())
    lbl.bind("<Enter>", lambda _e: lbl.configure(fg=C_GOLD))
    lbl.bind("<Leave>", lambda _e: lbl.configure(fg=fg))
    return lbl


class UpdateDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Tk,
        info: ReleaseInfo,
        on_skip: Callable[[str], None],
        on_ready_to_quit: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self.info = info
        self._on_skip = on_skip
        self._on_ready_to_quit = on_ready_to_quit
        self._progress: tuple[int, int] = (0, 0)
        self._result: Exception | None | bool = None  # True = başarılı
        self._busy = False
        self._icons = IconStore()
        self._photos: list = []
        self.blocker = self_update_blocker()

        self.title("Güncelleme mevcut")
        self.configure(bg=C_BG)
        self.resizable(False, False)
        self.transient(parent)

        self._build_header()
        self._build_body()
        self._build_footer()

        self.protocol("WM_DELETE_WINDOW", self._close)
        self._center_on(parent)
        self.lift()
        self.focus_force()

    # ── Bölümler ─────────────────────────────────────────────────────

    def _build_header(self) -> None:
        head = tk.Frame(self, bg=C_PRIMARY)
        head.pack(fill="x")
        inner = tk.Frame(head, bg=C_PRIMARY)
        inner.pack(fill="x", padx=24, pady=20)

        logo = self._load_logo(56)
        if logo is not None:
            tk.Label(inner, image=logo, bg=C_PRIMARY).pack(side="left", padx=(0, 16))

        titles = tk.Frame(inner, bg=C_PRIMARY)
        titles.pack(side="left", fill="x")
        tk.Label(
            titles, text="GÜNCELLEME MEVCUT", font=("Segoe UI Semibold", 8),
            fg=C_GOLD, bg=C_PRIMARY,
        ).pack(anchor="w")
        tk.Label(
            titles, text=f"{APP_DISPLAY} {self.info.version}",
            font=("Segoe UI Semibold", 16), fg="#FFFFFF", bg=C_PRIMARY,
        ).pack(anchor="w", pady=(2, 0))
        tk.Label(
            titles, text="Yeni sürüm indirilmeye hazır",
            font=("Segoe UI", 10), fg=C_HEAD_SUB, bg=C_PRIMARY,
        ).pack(anchor="w")

        # Altın ince şerit
        tk.Frame(self, bg=C_GOLD, height=3).pack(fill="x")

    def _build_body(self) -> None:
        body = tk.Frame(self, bg=C_BG)
        body.pack(fill="both", expand=True, padx=24, pady=(18, 8))

        # Sürüm karşılaştırma şeridi
        strip = tk.Frame(body, bg=C_SOFT, highlightbackground=C_LINE, highlightthickness=1)
        strip.pack(fill="x")
        row = tk.Frame(strip, bg=C_SOFT)
        row.pack(padx=16, pady=10, anchor="w")
        self._version_pill(row, "Kullandığınız", f"v{current_version() or '?'}", C_MUTED)
        tk.Label(row, text="→", font=("Segoe UI", 14), fg=C_MUTED, bg=C_SOFT).pack(
            side="left", padx=14
        )
        self._version_pill(row, "Yeni sürüm", f"v{self.info.version}", C_GOLD)

        # Yenilikler
        tk.Label(
            body, text="Bu sürümde neler var?", font=("Segoe UI Semibold", 11),
            fg=C_NAVY, bg=C_BG,
        ).pack(anchor="w", pady=(16, 6))
        items = release_highlights(self.info.notes) or [
            "Hata düzeltmeleri ve performans iyileştirmeleri"
        ]
        notes = tk.Text(
            body, wrap="word", font=("Segoe UI", 10), relief="flat", bg=C_BG,
            fg="#2B3440", highlightthickness=0, borderwidth=0, cursor="arrow",
            height=min(8, max(2, len(items) + 1)), width=58,
        )
        notes.tag_configure("dot", foreground=C_GOLD, font=("Segoe UI Semibold", 10))
        notes.tag_configure("item", lmargin1=0, lmargin2=18, spacing1=2, spacing3=4)
        for text in items:
            notes.insert("end", "●  ", ("dot", "item"))
            notes.insert("end", text + "\n", "item")
        notes.configure(state="disabled")
        notes.pack(fill="x")

        # Güvence / engel bildirimi
        if self.blocker:
            box = tk.Frame(body, bg=C_NOTICE_BG)
            box.pack(fill="x", pady=(10, 0))
            tk.Label(
                box,
                text=f"{self.blocker}\nYeni sürümü ürün sayfasından indirebilirsiniz.",
                font=("Segoe UI", 9), fg=C_NOTICE_FG, bg=C_NOTICE_BG,
                justify="left", wraplength=470,
            ).pack(anchor="w", padx=12, pady=8)
        else:
            safe = tk.Frame(body, bg=C_BG)
            safe.pack(fill="x", pady=(10, 0))
            ic = self._icons.get("shield-halved", size=13, fill="#2E7D4F")
            if ic is not None:
                tk.Label(safe, image=ic, bg=C_BG).pack(side="left", padx=(0, 8))
            tk.Label(
                safe,
                text="Program kapanıp yeni sürümle yeniden açılır. Ayarlarınız ve "
                "Excel dosyalarınız korunur.",
                font=("Segoe UI", 9), fg=C_MUTED, bg=C_BG, wraplength=440,
                justify="left",
            ).pack(side="left", anchor="w")

        # İlerleme (güncelleme başlayınca görünür)
        self.progress_box = tk.Frame(body, bg=C_BG)
        self.bar = ttk.Progressbar(self.progress_box, maximum=100)
        self.bar.pack(fill="x")
        self.status_var = tk.StringVar()
        tk.Label(
            self.progress_box, textvariable=self.status_var, font=("Segoe UI", 9),
            fg=C_NAVY, bg=C_BG,
        ).pack(anchor="w", pady=(4, 0))

    def _build_footer(self) -> None:
        tk.Frame(self, bg=C_LINE, height=1).pack(fill="x", pady=(8, 0))
        foot = tk.Frame(self, bg=C_BG)
        foot.pack(fill="x", padx=24, pady=14)

        left = tk.Frame(foot, bg=C_BG)
        left.pack(side="left", anchor="w")
        page_row = tk.Frame(left, bg=C_BG)
        page_row.pack(anchor="w")
        ic = self._icons.get("globe", size=12, fill=C_NAVY)
        if ic is not None:
            tk.Label(page_row, image=ic, bg=C_BG).pack(side="left", padx=(0, 6))
        _link(page_row, PRODUCT_PAGE_LABEL, self._open_page).pack(side="left")
        tk.Label(
            left, text="Mac ve Windows sürümleri", font=("Segoe UI", 8),
            fg=C_MUTED, bg=C_BG,
        ).pack(anchor="w")
        self.skip_link = _link(left, "Bu sürümü atla", self._skip, size=8, fg=C_MUTED)
        self.skip_link.pack(anchor="w", pady=(6, 0))

        self.btn_update = _Button(
            foot,
            "İndirme sayfasını aç" if self.blocker else "Şimdi güncelle",
            self._update,
            primary=True,
        )
        self.btn_update.pack(side="right")
        self.btn_later = _Button(foot, "Sonra", self._close)
        self.btn_later.pack(side="right", padx=(0, 8))

    # ── Yardımcılar ──────────────────────────────────────────────────

    def _version_pill(self, parent, caption: str, value: str, color: str) -> None:
        box = tk.Frame(parent, bg=C_SOFT)
        box.pack(side="left")
        tk.Label(box, text=caption, font=("Segoe UI", 8), fg=C_MUTED, bg=C_SOFT).pack(
            anchor="w"
        )
        tk.Label(
            box, text=value, font=("Segoe UI Semibold", 13), fg=color, bg=C_SOFT
        ).pack(anchor="w")

    def _load_logo(self, size: int):
        path = assets_dir() / "app.png"
        if not path.exists():
            return None
        try:
            from PIL import Image, ImageTk

            img = Image.open(path).convert("RGBA").resize(
                (size, size), Image.Resampling.LANCZOS
            )
            photo = ImageTk.PhotoImage(img)
            self._photos.append(photo)
            return photo
        except Exception:
            return None

    def _center_on(self, parent: tk.Misc) -> None:
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        try:
            x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
            y = parent.winfo_rooty() + (parent.winfo_height() - h) // 3
        except tk.TclError:
            x = (self.winfo_screenwidth() - w) // 2
            y = (self.winfo_screenheight() - h) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _set_buttons(self, on: bool) -> None:
        self.btn_update.set_enabled(on)
        self.btn_later.set_enabled(on)
        self.skip_link.configure(cursor="hand2" if on else "arrow")

    def _open_page(self) -> None:
        webbrowser.open(PRODUCT_PAGE)

    # ── Eylemler ─────────────────────────────────────────────────────

    def _close(self) -> None:
        if not self._busy:
            self.destroy()

    def _skip(self) -> None:
        if self._busy:
            return
        self._on_skip(self.info.version)
        self.destroy()

    def _update(self) -> None:
        if self.blocker:
            self._open_page()
            self.destroy()
            return
        self._busy = True
        self._set_buttons(False)
        self.progress_box.pack(fill="x", pady=(14, 0))
        self.status_var.set("İndiriliyor…")

        def progress(done: int, total: int) -> None:
            self._progress = (done, total)

        def work() -> None:
            try:
                install_update(self.info, progress)
                self._result = True
            except Exception as exc:
                self._result = exc

        threading.Thread(target=work, daemon=True).start()
        self.after(150, self._poll)

    def _poll(self) -> None:
        done, total = self._progress
        if total:
            self.bar.configure(value=done * 100 / total)
            self.status_var.set(
                f"İndiriliyor…  {done / 1048576:.1f} / {total / 1048576:.1f} MB"
            )
        if self._result is None:
            self.after(150, self._poll)
            return
        self._busy = False
        if self._result is True:
            self.bar.configure(value=100)
            self.status_var.set("Kuruluyor — program birkaç saniye içinde yeniden açılacak…")
            self.after(800, self._on_ready_to_quit)
            return
        err = self._result
        self._result = None
        self._set_buttons(True)
        self.progress_box.pack_forget()
        if messagebox.askyesno(
            "Güncelleme",
            f"Güncelleme tamamlanamadı:\n{err}\n\n"
            f"Yeni sürümü {PRODUCT_PAGE_LABEL} sayfasından indirmek ister misiniz?",
            parent=self,
        ):
            self._open_page()
