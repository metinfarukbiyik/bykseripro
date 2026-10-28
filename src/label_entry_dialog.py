"""Listeye elle tek seri ekleme penceresi (Excel'i açmadan)."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from excel_loader import ColumnHeaders, role_label
from tspl_builder import LabelData

ROLES = ("barkod", "ak_barkod", "item_no", "parca_ad")


class LabelEntryDialog(tk.Toplevel):
    """
    Açık kalır: her "Ekle" bir satır ekler ve alanları boşaltır.
    on_add(label) True dönerse eklenmiş sayılır.
    """

    def __init__(
        self,
        parent: tk.Tk,
        headers: ColumnHeaders,
        on_add: Callable[[LabelData], bool],
        exists: Callable[[str], bool],
    ) -> None:
        super().__init__(parent)
        self._on_add = on_add
        self._exists = exists
        self.title("Seri ekle")
        self.resizable(False, False)
        self.transient(parent)

        body = ttk.Frame(self, padding=14)
        body.pack(fill="both", expand=True)
        ttk.Label(
            body,
            text="Listeye tek bir seri ekleyin. Excel dosyası değişmez.",
            foreground="#6B7380",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.vars: dict[str, tk.StringVar] = {}
        self._first: ttk.Entry | None = None
        for i, role in enumerate(ROLES, start=1):
            text = role_label(role, headers) + (" *" if role == "barkod" else "")
            ttk.Label(body, text=text + ":").grid(row=i, column=0, sticky="e", padx=(0, 8), pady=3)
            var = tk.StringVar()
            entry = ttk.Entry(body, textvariable=var, width=36)
            entry.grid(row=i, column=1, sticky="w", pady=3)
            self.vars[role] = var
            if self._first is None:
                self._first = entry

        self.status_var = tk.StringVar()
        self.status = ttk.Label(body, textvariable=self.status_var, foreground="#2E7D4F")
        self.status.grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))

        btns = ttk.Frame(body)
        btns.grid(row=6, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(btns, text="Kapat", command=self.destroy).pack(side="right")
        ttk.Button(btns, text="Ekle", command=self._add, style="Primary.TButton").pack(
            side="right", padx=(0, 6)
        )

        self.bind("<Return>", lambda _e: self._add())
        self.bind("<Escape>", lambda _e: self.destroy())
        self._center_on(parent)
        if self._first is not None:
            self._first.focus_set()

    def _center_on(self, parent: tk.Misc) -> None:
        """Program penceresinin yatay ve dikey ortasında aç."""
        self.withdraw()
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        # geometry() çerçeveyi (başlık çubuğu dahil) konumlar; ölçüler içerik alanı
        bar = max(0, parent.winfo_rooty() - parent.winfo_y())
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2 - bar
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.deiconify()

    def _add(self) -> None:
        values = {role: var.get().strip() for role, var in self.vars.items()}
        barkod = values["barkod"]
        if not barkod:
            self.status.configure(foreground="#D93025")
            self.status_var.set("Ana barkod / seri no boş olamaz.")
            return
        if self._exists(barkod) and not messagebox.askyesno(
            "Seri ekle",
            f"“{barkod}” listede zaten var.\nYine de eklensin mi?",
            parent=self,
        ):
            return
        label = LabelData(
            barkod=barkod,
            ak_barkod=values["ak_barkod"],
            item_no=values["item_no"],
            parca_ad=values["parca_ad"],
        )
        if not self._on_add(label):
            return
        self.status.configure(foreground="#2E7D4F")
        self.status_var.set(f"Eklendi: {barkod}")
        # Ana barkod temizlenir; diğer alanlar sonraki seri için kalır
        self.vars["barkod"].set("")
        if self._first is not None:
            self._first.focus_set()
