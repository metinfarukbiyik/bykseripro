"""
Yerleşim ayarları — etiketin kağıtta nasıl görüneceğini kullanıcı yönetir.

Değişkenler ana penceredeki (LabelApp) tk değişkenlerine bağlıdır; her
değişiklik hem ana önizlemeyi hem bu penceredeki büyük önizlemeyi yeniler.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from excel_loader import role_label
from label_preview import render_label_photoimage
from tspl_builder import AK_POSITIONS, TEXT_MODES, compute_layout
from ui_icons import C_GOLD, C_NAVY, C_TEAL, icon_button, icon_labelframe

if TYPE_CHECKING:
    from main_window import LabelApp

# Ön ayarlar: değişken adı → değer
PRESET_DEFAULT = {
    "ak_pos_var": "below",
    "auto_fit_var": True,
    "max_lines_var": "2",
    "text_mode_var": "graphic",
    "margin_var": "6",
    "gap_after_bc_var": "1.5",
    "gap_barcodes_var": "4",
    "gap_text_var": "2.5",
    "offset_x_var": "0",
    "offset_y_var": "0",
    "narrow_var": "3",
    "show_main_text_var": True,
    "show_ak_var": True,
    "show_ak_text_var": True,
    "show_item_var": True,
    "show_parca_var": True,
}

PRESET_NARROW = {
    **PRESET_DEFAULT,
    "ak_pos_var": "side",
    "margin_var": "2",
    "gap_after_bc_var": "0.8",
    "gap_barcodes_var": "2",
    "gap_text_var": "1",
}


class LayoutDialog(tk.Toplevel):
    def __init__(self, app: "LabelApp") -> None:
        super().__init__(app)
        self.app = app
        self.title("Yerleşim ayarları — kağıtta görünüm")
        self.geometry("1040x660")
        self.minsize(860, 560)
        self.transient(app)
        self._photo = None
        self._after: str | None = None

        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=0)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        left = ttk.Frame(root)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 10))
        self._build_controls(left)

        right = icon_labelframe(
            root, "Kağıt önizlemesi (yazıcıyla birebir)", "eye", app._icons, fill=C_TEAL
        )
        right.grid(row=0, column=1, sticky="nsew")
        self.canvas = tk.Canvas(right, bg="#F0F0F0", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=6, pady=6)
        self.canvas.bind("<Configure>", lambda _e: self.refresh())
        self.note_var = tk.StringVar()
        self.note_lbl = ttk.Label(
            right, textvariable=self.note_var, wraplength=520, justify="left"
        )
        self.note_lbl.pack(fill="x", padx=8, pady=(0, 6))
        ttk.Label(
            right,
            text="Kesikli çizgi kenar boşluğunu gösterir (basılmaz). "
            "Kırmızı çerçeve: içerik etikete sığmıyor.",
            foreground="#6B7380",
        ).pack(fill="x", padx=8, pady=(0, 6))

        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(50, self.refresh)

    # ── Kontroller ───────────────────────────────────────────────────

    def _build_controls(self, parent: ttk.Frame) -> None:
        a = self.app
        pad = {"padx": 6, "pady": 3}
        h = a.column_headers

        size = icon_labelframe(parent, "Etiket ve barkod (mm)", "ruler-combined", a._icons, fill=C_NAVY)
        size.pack(fill="x", pady=(0, 6))
        self._spin(size, "Genişlik", a.width_var, 0, 0, 10, 120, 1)
        self._spin(size, "Yükseklik", a.height_var, 0, 2, 10, 200, 1)
        self._spin(size, "Ana barkod yük.", a.bc_height_var, 1, 0, 3, 80, 0.5)
        self._spin(size, "2. barkod yük.", a.ak_bc_height_var, 1, 2, 3, 80, 0.5)
        self._spin(size, "Çizgi kalınlığı", a.narrow_var, 2, 0, 1, 6, 1)

        fields = icon_labelframe(parent, "Basılacak alanlar", "list-check", a._icons, fill=C_NAVY)
        fields.pack(fill="x", pady=6)
        checks = [
            (f"{role_label('barkod', h)} metni", a.show_main_text_var),
            (role_label("ak_barkod", h), a.show_ak_var),
            ("2. barkod metni", a.show_ak_text_var),
            (role_label("item_no", h), a.show_item_var),
            (role_label("parca_ad", h), a.show_parca_var),
        ]
        for i, (text, var) in enumerate(checks):
            ttk.Checkbutton(fields, text=text, variable=var).grid(
                row=i // 2, column=i % 2, sticky="w", **pad
            )

        arr = icon_labelframe(parent, "Düzen", "table-cells", a._icons, fill=C_NAVY)
        arr.pack(fill="x", pady=6)
        ttk.Label(arr, text="2. barkod:").grid(row=0, column=0, sticky="e", **pad)
        for i, (key, text) in enumerate(AK_POSITIONS.items()):
            ttk.Radiobutton(arr, text=text, value=key, variable=a.ak_pos_var).grid(
                row=0, column=1 + i, sticky="w", **pad
            )
        ttk.Checkbutton(
            arr,
            text="Otomatik sığdır (boşluk / barkod / font küçültülür)",
            variable=a.auto_fit_var,
        ).grid(row=1, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(arr, text="Uzun metin en fazla:").grid(row=2, column=0, sticky="e", **pad)
        sp = ttk.Spinbox(arr, from_=1, to=4, increment=1, width=5, textvariable=a.max_lines_var)
        sp.grid(row=2, column=1, sticky="w", **pad)
        ttk.Label(arr, text="satır").grid(row=2, column=2, sticky="w", **pad)
        ttk.Label(arr, text="Metin basımı:").grid(row=3, column=0, sticky="e", **pad)
        mode = ttk.Combobox(
            arr,
            values=[f"{k} — {v}" for k, v in TEXT_MODES.items()],
            state="readonly",
            width=34,
        )
        cur = a.text_mode_var.get()
        mode.set(f"{cur} — {TEXT_MODES.get(cur, '')}")
        mode.grid(row=3, column=1, columnspan=2, sticky="w", **pad)

        def on_mode(_e=None) -> None:
            raw = (mode.get() or "graphic").split("—", 1)[0].strip()
            a.text_mode_var.set(raw if raw in TEXT_MODES else "graphic")

        mode.bind("<<ComboboxSelected>>", on_mode)
        self._mode_combo = mode

        gaps = icon_labelframe(parent, "Boşluklar (mm)", "arrows-up-down", a._icons, fill=C_NAVY)
        gaps.pack(fill="x", pady=6)
        self._spin(gaps, "Kenar boşluğu", a.margin_var, 0, 0, 0, 20, 0.5)
        self._spin(gaps, "Barkod → metin", a.gap_after_bc_var, 0, 2, 0, 10, 0.5)
        self._spin(gaps, "Barkodlar arası", a.gap_barcodes_var, 1, 0, 0, 20, 0.5)
        self._spin(gaps, "Metin satırları", a.gap_text_var, 1, 2, 0, 10, 0.5)

        cal = icon_labelframe(parent, "Yazıcı kalibrasyonu (mm)", "crosshairs", a._icons, fill=C_NAVY)
        cal.pack(fill="x", pady=6)
        self._spin(cal, "Yatay kaydır (+sağ)", a.offset_x_var, 0, 0, -20, 20, 0.5)
        self._spin(cal, "Dikey kaydır (+aşağı)", a.offset_y_var, 0, 2, -20, 20, 0.5)

        btns = ttk.Frame(parent)
        btns.pack(fill="x", pady=(8, 0))
        icon_button(
            btns, "Dar etiket önerisi", "compress", lambda: self._apply(PRESET_NARROW),
            a._icons, fill=C_GOLD,
        ).pack(side="left")
        icon_button(
            btns, "Varsayılan", "rotate-left", lambda: self._apply(PRESET_DEFAULT), a._icons,
        ).pack(side="left", padx=6)
        icon_button(
            btns, "Kaydet ve kapat", "floppy-disk", self._save_close, a._icons, fill=C_TEAL,
        ).pack(side="right")

    def _spin(self, parent, label, var, row, col, lo, hi, step) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="e", padx=6, pady=3)
        ttk.Spinbox(
            parent, from_=lo, to=hi, increment=step, width=7, textvariable=var
        ).grid(row=row, column=col + 1, sticky="w", padx=6, pady=3)

    def _apply(self, preset: dict) -> None:
        for name, value in preset.items():
            getattr(self.app, name).set(value)
        cur = self.app.text_mode_var.get()
        self._mode_combo.set(f"{cur} — {TEXT_MODES.get(cur, '')}")

    def _save_close(self) -> None:
        self.app.persist_settings()
        self._close()

    def _close(self) -> None:
        self.app._layout_dialog = None
        self.destroy()

    # ── Önizleme ─────────────────────────────────────────────────────

    def refresh(self) -> None:
        if self._after is not None:
            self.after_cancel(self._after)
        self._after = self.after(80, self._draw)

    def _draw(self) -> None:
        self._after = None
        if not self.winfo_exists():
            return
        label = self.app.preview_label()
        cw = max(80, self.canvas.winfo_width())
        ch = max(80, self.canvas.winfo_height())
        self.canvas.delete("all")
        try:
            settings = self.app.settings_from_ui()
            photo, _ = render_label_photoimage(label, settings, max_size=(cw - 16, ch - 16))
            self._photo = photo
            self.canvas.create_image(cw // 2, ch // 2, image=photo)
            layout = compute_layout(label, settings)
            self.note_var.set(layout.fit_note or "İçerik etikete sığıyor.")
            self.note_lbl.configure(foreground="#D93025" if layout.overflow else "#2E7D4F")
        except ValueError as exc:
            self.note_var.set(str(exc))
            self.note_lbl.configure(foreground="#D93025")
