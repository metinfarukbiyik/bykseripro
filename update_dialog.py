"""Güncelleme bildirimi — yeni sürümü gösterir, indirir ve kurar."""

from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk
from typing import Callable

from branding import APP_DISPLAY
from ui_icons import C_GOLD, C_MUTED, C_NAVY, C_TEAL
from updater import ReleaseInfo, current_version, install_update, self_update_blocker


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

        self.title("Güncelleme mevcut")
        self.geometry("560x440")
        self.minsize(460, 360)
        self.transient(parent)
        self.configure(bg="#FFFFFF")

        body = tk.Frame(self, bg="#FFFFFF")
        body.pack(fill="both", expand=True, padx=18, pady=14)

        tk.Label(
            body,
            text="Yeni sürüm hazır",
            font=("Segoe UI Semibold", 14),
            fg=C_NAVY,
            bg="#FFFFFF",
        ).pack(anchor="w")
        tk.Label(
            body,
            text=(
                f"{APP_DISPLAY} v{info.version} yayınlandı.  "
                f"Kullandığınız sürüm: v{current_version() or '?'}"
            ),
            font=("Segoe UI", 10),
            fg=C_GOLD,
            bg="#FFFFFF",
        ).pack(anchor="w", pady=(2, 10))

        notes = tk.Text(
            body, height=10, wrap="word", font=("Segoe UI", 9), relief="flat",
            bg="#F6F8FA", padx=8, pady=6,
        )
        notes.insert("1.0", info.notes or "Sürüm notu yok.")
        notes.configure(state="disabled")
        notes.pack(fill="both", expand=True)

        self.blocker = self_update_blocker()
        hint = (
            "“Şimdi güncelle” paketi indirir; uygulama kapanır, yeni sürüm kurulup "
            "otomatik açılır. Ayarlarınız ve Excel dosyalarınız korunur."
        )
        if self.blocker:
            hint = f"{self.blocker}\nİndirme sayfası tarayıcıda açılacak."
        tk.Label(
            body, text=hint, font=("Segoe UI", 9), fg=C_MUTED, bg="#FFFFFF",
            justify="left", wraplength=500,
        ).pack(anchor="w", pady=(8, 4))

        self.bar = ttk.Progressbar(body, maximum=100)
        self.status_var = tk.StringVar()
        tk.Label(
            body, textvariable=self.status_var, font=("Segoe UI", 9), fg=C_TEAL,
            bg="#FFFFFF",
        ).pack(anchor="w")

        btns = tk.Frame(body, bg="#FFFFFF")
        btns.pack(fill="x", pady=(8, 0))
        self.btn_update = ttk.Button(
            btns,
            text="İndirme sayfasını aç" if self.blocker else "Şimdi güncelle",
            command=self._update,
        )
        self.btn_update.pack(side="right")
        self.btn_later = ttk.Button(btns, text="Sonra", command=self.destroy)
        self.btn_later.pack(side="right", padx=6)
        self.btn_skip = ttk.Button(btns, text="Bu sürümü atla", command=self._skip)
        self.btn_skip.pack(side="left")

        self.protocol("WM_DELETE_WINDOW", self._close)
        self.lift()
        self.focus_force()

    def _close(self) -> None:
        if not self._busy:
            self.destroy()

    def _skip(self) -> None:
        self._on_skip(self.info.version)
        self.destroy()

    def _update(self) -> None:
        if self.blocker:
            webbrowser.open(self.info.page_url)
            self.destroy()
            return
        self._busy = True
        for b in (self.btn_update, self.btn_later, self.btn_skip):
            b.configure(state="disabled")
        self.bar.pack(fill="x", pady=(6, 2), before=self.btn_update.master)
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
                f"İndiriliyor… {done / 1048576:.1f} / {total / 1048576:.1f} MB"
            )
        if self._result is None:
            self.after(150, self._poll)
            return
        self._busy = False
        if self._result is True:
            self.bar.configure(value=100)
            self.status_var.set("Kuruluyor — uygulama yeniden açılacak…")
            self.after(800, self._on_ready_to_quit)
            return
        err = self._result
        self._result = None
        for b in (self.btn_update, self.btn_later, self.btn_skip):
            b.configure(state="normal")
        self.status_var.set("")
        if messagebox.askyesno(
            "Güncelleme",
            f"Güncelleme yapılamadı:\n{err}\n\nİndirme sayfası açılsın mı?",
            parent=self,
        ):
            webbrowser.open(self.info.page_url)
