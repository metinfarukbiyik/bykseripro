"""
Yerleşim ayarları — etiketin kağıtta nasıl görüneceğini kullanıcı yönetir.

Sol: sekmeli ayrıntılı ayarlar (Etiket · Barkodlar · Metinler · Konum).
Sağ: etkileşimli önizleme — öğeye tıklayıp sürükleyerek taşınır, ok tuşlarıyla
ince ayar yapılır; etiket dışına taşan öğe kırmızı çerçevelenir ve
"Sorunları otomatik düzelt" ile tek tıkla sığdırılır.

Değişkenler ana penceredeki (LabelApp) tk değişkenlerine bağlıdır; her
değişiklik hem ana önizlemeyi hem bu penceredeki önizlemeyi yeniler.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from excel_loader import role_label
from label_preview import render_label_photoimage
from theme import MUTED, PAGE
from tspl_builder import (
    AK_POSITIONS,
    ALIGNMENTS,
    ELEMENT_GROUPS,
    FONT_SIZE_LABELS,
    TEXT_MODES,
    VALIGNS,
    compute_layout,
    dots_per_mm,
)
from ui_icons import C_NAVY, icon_button, icon_labelframe

if TYPE_CHECKING:
    from main_window import LabelApp

OK_GREEN = "#1F8A5B"
ERR_RED = "#C62828"
SNAP_MM = 1.2  # ortaya yaslanma mesafesi
NUDGE_MM, NUDGE_FAST_MM = 0.5, 2.0

# Geri al / ön ayarlar için izlenen değişkenler (LabelApp öznitelik adları)
TRACKED_VARS = (
    "width_var", "height_var", "margin_var", "valign_var", "direction_var",
    "auto_fit_var", "max_lines_var", "text_mode_var",
    "bc_height_var", "narrow_var", "show_main_text_var", "font_barkod_var",
    "show_ak_var", "ak_bc_height_var", "ak_narrow_var", "show_ak_text_var",
    "font_ak_var", "ak_pos_var", "qr_cell_var",
    "gap_after_bc_var", "gap_barcodes_var", "gap_text_var",
    "show_item_var", "font_item_var", "show_parca_var", "font_parca_var",
    "font_brand_var", "offset_x_var", "offset_y_var",
)

PRESET_DEFAULT = {
    "ak_pos_var": "below", "auto_fit_var": True, "max_lines_var": "2",
    "text_mode_var": "graphic", "margin_var": "6", "valign_var": "center",
    "gap_after_bc_var": "1.5", "gap_barcodes_var": "4", "gap_text_var": "2.5",
    "offset_x_var": "0", "offset_y_var": "0", "narrow_var": "3", "ak_narrow_var": "0",
    "qr_cell_var": "4", "font_parca_var": 0,
    "show_main_text_var": True, "show_ak_var": True, "show_ak_text_var": True,
    "show_item_var": True, "show_parca_var": True,
}
PRESET_NARROW = {
    **PRESET_DEFAULT,
    "ak_pos_var": "side", "margin_var": "2",
    "gap_after_bc_var": "0.8", "gap_barcodes_var": "2", "gap_text_var": "1",
}


class LayoutDialog(tk.Toplevel):
    def __init__(self, app: "LabelApp") -> None:
        super().__init__(app)
        self.app = app
        self.title("Yerleşim ayarları — kağıtta görünüm")
        self.configure(bg=PAGE)
        self.minsize(1000, 660)
        self.transient(app)

        self.selected: str | None = None
        self._layout = None
        self._scale = 1.0
        self._origin = (0, 0)
        self._drag: dict | None = None
        self._snapped = False
        self._undo: list[dict] = []
        self._quiet = False  # programatik değişiklikte ana önizlemeyi yenileme
        self._photo = None
        self._after: str | None = None
        self._note_locked = False  # otomatik düzeltme raporu bir çizim boyunca kalsın

        self.align_vars: dict[str, tk.StringVar] = {}
        self.off_vars: dict[str, tuple[tk.StringVar, tk.StringVar]] = {}
        for group in ELEMENT_GROUPS:
            av = tk.StringVar(value=app.element_align.get(group, "center"))
            av.trace_add("write", lambda *_a, g=group: self._on_align(g))
            dx, dy = app.element_offsets.get(group, [0.0, 0.0])
            xv, yv = tk.StringVar(value=_fmt(dx)), tk.StringVar(value=_fmt(dy))
            xv.trace_add("write", lambda *_a, g=group: self._on_offset_var(g))
            yv.trace_add("write", lambda *_a, g=group: self._on_offset_var(g))
            self.align_vars[group] = av
            self.off_vars[group] = (xv, yv)

        root = ttk.Frame(self, padding=12, style="Page.TFrame")
        root.pack(fill="both", expand=True)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        left = ttk.Frame(root, style="Page.TFrame")
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        self._build_tabs(left)
        self._build_footer(left)

        right = icon_labelframe(
            root, "Kağıt önizlemesi — öğeleri sürükleyerek yerleştirin", "eye",
            app._icons, fill=C_NAVY,
        )
        right.grid(row=0, column=1, sticky="nsew")
        self._build_preview(right)

        self.protocol("WM_DELETE_WINDOW", self._close)
        for seq in ("<Control-z>", "<Command-z>"):
            self.bind(seq, lambda _e: self.undo())
        self._center_on(app)
        self.after(60, self.refresh)

    # ── Yerleşim yardımcıları ────────────────────────────────────────

    def _center_on(self, parent: tk.Misc) -> None:
        w, h = 1180, max(660, min(780, parent.winfo_height()))
        bar = max(0, parent.winfo_rooty() - parent.winfo_y())
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2 - bar
        self.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")

    def _section(self, parent, text: str, row: int) -> int:
        ttk.Label(parent, text=text, style="Section.TLabel").grid(
            row=row, column=0, columnspan=6, sticky="w", padx=4, pady=(10 if row else 2, 2)
        )
        return row + 1

    def _spin(self, parent, label, var, row, col, lo, hi, step, unit="mm", width=6) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="e", padx=(6, 4), pady=2)
        cell = ttk.Frame(parent)
        cell.grid(row=row, column=col + 1, sticky="w", pady=2)
        ttk.Spinbox(
            cell, from_=lo, to=hi, increment=step, width=width, textvariable=var
        ).pack(side="left")
        if unit:
            ttk.Label(cell, text=unit, style="Muted.TLabel").pack(side="left", padx=(4, 0))

    def _check(self, parent, text, var, row, col=0, span=2) -> None:
        ttk.Checkbutton(parent, text=text, variable=var).grid(
            row=row, column=col, columnspan=span, sticky="w", padx=4, pady=2
        )

    def _radios(self, parent, label, var, options: dict, row, col=0) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="e", padx=(6, 4), pady=2)
        cell = ttk.Frame(parent)
        cell.grid(row=row, column=col + 1, columnspan=3, sticky="w", pady=2)
        for key, text in options.items():
            ttk.Radiobutton(cell, text=text, value=key, variable=var).pack(side="left", padx=(0, 10))

    def _align_combo(self, parent, group: str) -> ttk.Combobox:
        """Hiza seçimi: Türkçe ad gösterir, iç değeri (left/center/right) yazar."""
        var = self.align_vars[group]
        combo = ttk.Combobox(parent, values=list(ALIGNMENTS.values()), state="readonly", width=7)

        def sync(*_a) -> None:
            if combo.winfo_exists():
                combo.set(ALIGNMENTS.get(var.get(), ALIGNMENTS["center"]))

        sync()
        var.trace_add("write", sync)
        names = {v: k for k, v in ALIGNMENTS.items()}
        combo.bind("<<ComboboxSelected>>", lambda _e: var.set(names.get(combo.get(), "center")))
        return combo

    def _font_combo(self, parent, label, var: tk.IntVar, row, col=0, same_as=None) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="e", padx=(6, 4), pady=2)
        values = {k: f"{k} — {v}" for k, v in FONT_SIZE_LABELS.items()}
        if same_as:
            values = {0: f"0 — {same_as}", **values}
        combo = ttk.Combobox(parent, values=list(values.values()), state="readonly", width=20)
        combo.grid(row=row, column=col + 1, columnspan=3, sticky="w", pady=2)

        def sync(*_a) -> None:
            if combo.winfo_exists():
                combo.set(values.get(int(var.get()), values[min(values)]))

        def pick(_e=None) -> None:
            var.set(int(combo.get().split("—", 1)[0].strip() or 0))

        sync()
        var.trace_add("write", sync)
        combo.bind("<<ComboboxSelected>>", pick)

    # ── Sekmeler ─────────────────────────────────────────────────────

    def _build_tabs(self, parent) -> None:
        a = self.app
        h = a.column_headers
        tabs = ttk.Notebook(parent, width=430)
        tabs.pack(fill="both", expand=True)

        # Etiket
        t = ttk.Frame(tabs, padding=(8, 6))
        tabs.add(t, text="Etiket")
        r = self._section(t, "Kağıt", 0)
        self._spin(t, "Genişlik", a.width_var, r, 0, 10, 200, 1)
        self._spin(t, "Yükseklik", a.height_var, r, 2, 10, 300, 1)
        self._spin(t, "Kenar boşluğu", a.margin_var, r + 1, 0, 0, 20, 0.5)
        r = self._section(t, "İçerik", r + 2)
        self._radios(t, "Dikey hiza", a.valign_var, VALIGNS, r)
        self._check(t, "Otomatik sığdır (boşluk / barkod / font küçültülür)", a.auto_fit_var, r + 1, span=4)
        self._spin(t, "Uzun metin en fazla", a.max_lines_var, r + 2, 0, 1, 4, 1, unit="satır")
        ttk.Label(t, text="Metin basımı").grid(row=r + 3, column=0, sticky="e", padx=(6, 4), pady=2)
        mode = ttk.Combobox(
            t, values=[f"{k} — {v}" for k, v in TEXT_MODES.items()], state="readonly", width=34
        )
        mode.grid(row=r + 3, column=1, columnspan=3, sticky="w", pady=2)

        def mode_sync(*_x) -> None:
            if mode.winfo_exists():
                cur = a.text_mode_var.get()
                mode.set(f"{cur} — {TEXT_MODES.get(cur, '')}")

        mode_sync()
        a.text_mode_var.trace_add("write", mode_sync)
        mode.bind(
            "<<ComboboxSelected>>",
            lambda _e: a.text_mode_var.set(mode.get().split("—", 1)[0].strip() or "graphic"),
        )
        r = self._section(t, "Yazıcı", r + 4)
        self._radios(t, "Baskı yönü", a.direction_var, {"1": "Normal", "0": "Ters (180°)"}, r)
        ttk.Label(
            t, text="Etiketler yazıcıdan baş aşağı çıkıyorsa “Ters” seçin.",
            style="Muted.TLabel",
        ).grid(row=r + 1, column=0, columnspan=4, sticky="w", padx=6)

        # Barkodlar
        t = ttk.Frame(tabs, padding=(8, 6))
        tabs.add(t, text="Barkodlar")
        r = self._section(t, role_label("barkod", h), 0)
        self._spin(t, "Yükseklik", a.bc_height_var, r, 0, 3, 80, 0.5)
        self._spin(t, "Çizgi kalınlığı", a.narrow_var, r, 2, 1, 6, 1, unit="nokta", width=4)
        self._check(t, "Altına barkod metnini yaz", a.show_main_text_var, r + 1, span=4)
        self._font_combo(t, "Metin boyutu", a.font_barkod_var, r + 2)
        r = self._section(t, role_label("ak_barkod", h), r + 3)
        self._check(t, "2. barkodu bas", a.show_ak_var, r, span=4)
        self._spin(t, "Yükseklik", a.ak_bc_height_var, r + 1, 0, 3, 80, 0.5)
        self._spin(t, "Çizgi kalınlığı", a.ak_narrow_var, r + 1, 2, 0, 6, 1, unit="(0=oto)", width=4)
        self._check(t, "Altına barkod metnini yaz", a.show_ak_text_var, r + 2, span=4)
        self._font_combo(t, "Metin boyutu", a.font_ak_var, r + 3)
        self._radios(t, "Konum", a.ak_pos_var, AK_POSITIONS, r + 4)
        r = self._section(t, "QR kod ve boşluklar", r + 5)
        self._spin(t, "QR hücre", a.qr_cell_var, r, 0, 0, 10, 1, unit="(0=oto)", width=4)
        self._spin(t, "Barkod → metin", a.gap_after_bc_var, r + 1, 0, 0, 10, 0.5)
        self._spin(t, "Barkodlar arası", a.gap_barcodes_var, r + 1, 2, 0, 20, 0.5)
        ttk.Label(
            t, text="Çizgi kalınlığı arttıkça barkod genişler; sığmazsa otomatik inceltilir.",
            style="Muted.TLabel",
        ).grid(row=r + 2, column=0, columnspan=4, sticky="w", padx=6, pady=(4, 0))

        # Metinler
        t = ttk.Frame(tabs, padding=(8, 6))
        tabs.add(t, text="Metinler")
        r = self._section(t, role_label("item_no", h), 0)
        self._check(t, "Orta metni bas", a.show_item_var, r, span=4)
        self._font_combo(t, "Boyut", a.font_item_var, r + 1)
        self._radios(t, "Hizalama", self.align_vars["item"], ALIGNMENTS, r + 2)
        r = self._section(t, role_label("parca_ad", h), r + 3)
        self._check(t, "Alt metni bas", a.show_parca_var, r, span=4)
        self._font_combo(t, "Boyut", a.font_parca_var, r + 1, same_as="Orta metinle aynı")
        self._radios(t, "Hizalama", self.align_vars["parca"], ALIGNMENTS, r + 2)
        r = self._section(t, "Marka", r + 3)
        self._font_combo(t, "Boyut", a.font_brand_var, r)
        self._radios(t, "Hizalama", self.align_vars["brand"], ALIGNMENTS, r + 1)
        ttk.Label(
            t, text="Marka metni, konumu ve stili ana penceredeki “Fontlar ve markalama” sekmesinde.",
            style="Muted.TLabel", wraplength=400, justify="left",
        ).grid(row=r + 2, column=0, columnspan=4, sticky="w", padx=6)
        r = self._section(t, "Satır aralığı", r + 3)
        self._spin(t, "Metinler arası", a.gap_text_var, r, 0, 0, 10, 0.5)

        # Konum
        t = ttk.Frame(tabs, padding=(8, 6))
        tabs.add(t, text="Konum")
        r = self._section(t, "Öğe konumları (mm)", 0)
        ttk.Label(
            t, text="Önizlemede sürükleyerek de taşıyabilirsiniz. + sağa / aşağı.",
            style="Muted.TLabel",
        ).grid(row=r, column=0, columnspan=6, sticky="w", padx=6)
        for i, col_text in enumerate(("Öğe", "Yatay", "Dikey", "Hiza", "")):
            ttk.Label(t, text=col_text, style="Muted.TLabel").grid(row=r + 1, column=i, sticky="w", padx=4)
        for i, (group, name) in enumerate(ELEMENT_GROUPS.items()):
            row = r + 2 + i
            ttk.Label(t, text=name).grid(row=row, column=0, sticky="w", padx=4, pady=2)
            xv, yv = self.off_vars[group]
            for col, var in ((1, xv), (2, yv)):
                ttk.Spinbox(t, from_=-100, to=100, increment=0.5, width=6, textvariable=var).grid(
                    row=row, column=col, sticky="w", padx=2, pady=2
                )
            self._align_combo(t, group).grid(row=row, column=3, sticky="w", padx=2)
            ttk.Button(t, text="Sıfırla", command=lambda g=group: self.reset_group(g)).grid(
                row=row, column=4, sticky="w", padx=2
            )
        r += 2 + len(ELEMENT_GROUPS)
        ttk.Button(t, text="Tüm konumları sıfırla", command=self.reset_all).grid(
            row=r, column=0, columnspan=3, sticky="w", padx=4, pady=(6, 0)
        )
        r = self._section(t, "Yazıcı kalibrasyonu (tüm etiket)", r + 1)
        self._spin(t, "Yatay (+sağ)", a.offset_x_var, r, 0, -20, 20, 0.5)
        self._spin(t, "Dikey (+aşağı)", a.offset_y_var, r, 2, -20, 20, 0.5)
        ttk.Label(
            t, text="Baskı her etikette aynı yöne kayıyorsa buradan düzeltin.",
            style="Muted.TLabel",
        ).grid(row=r + 1, column=0, columnspan=6, sticky="w", padx=6)

        self.tabs = tabs

    def _build_footer(self, parent) -> None:
        a = self.app
        btns = ttk.Frame(parent, style="Page.TFrame")
        btns.pack(fill="x", pady=(10, 0))
        icon_button(
            btns, "Dar etiket", "compress", lambda: self._apply(PRESET_NARROW),
            a._icons, fill="#6E4E00", style="Warm.TButton",
        ).pack(side="left")
        icon_button(
            btns, "Varsayılan", "rotate-left", lambda: self._apply(PRESET_DEFAULT), a._icons,
        ).pack(side="left", padx=6)
        icon_button(
            btns, "Kaydet ve kapat", "floppy-disk", self._save_close, a._icons, fill="#FFFFFF",
            style="Primary.TButton",
        ).pack(side="right")

    def _build_preview(self, parent) -> None:
        a = self.app
        bar = ttk.Frame(parent)
        bar.pack(fill="x", pady=(0, 6))
        self.sel_title = ttk.Label(bar, text="", style="Section.TLabel")
        self.sel_title.pack(side="left", padx=(2, 10))
        self.sel_controls = ttk.Frame(bar)
        self.sel_controls.pack(side="left")
        ttk.Label(self.sel_controls, text="Yatay").pack(side="left")
        self.sel_x = ttk.Spinbox(self.sel_controls, from_=-100, to=100, increment=0.5, width=6)
        self.sel_x.pack(side="left", padx=(4, 8))
        ttk.Label(self.sel_controls, text="Dikey").pack(side="left")
        self.sel_y = ttk.Spinbox(self.sel_controls, from_=-100, to=100, increment=0.5, width=6)
        self.sel_y.pack(side="left", padx=(4, 10))
        self.sel_align: list[ttk.Radiobutton] = []
        for key, text in ALIGNMENTS.items():
            rb = ttk.Radiobutton(self.sel_controls, text=text, value=key)
            rb.pack(side="left", padx=(0, 6))
            self.sel_align.append(rb)
        icon_button(
            bar, "Konumu sıfırla", "rotate-left", lambda: self.selected and self.reset_group(self.selected),
            a._icons, size=12,
        ).pack(side="right")

        self.canvas = tk.Canvas(parent, bg="#F4F7FB", highlightthickness=0, cursor="arrow")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _e: self.refresh())
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Double-Button-1>", self._on_double)
        self.canvas.bind("<Motion>", self._on_hover)
        for key, dx, dy in (("Left", -1, 0), ("Right", 1, 0), ("Up", 0, -1), ("Down", 0, 1)):
            self.canvas.bind(f"<{key}>", lambda _e, x=dx, y=dy: self.nudge(x, y, NUDGE_MM))
            self.canvas.bind(f"<Shift-{key}>", lambda _e, x=dx, y=dy: self.nudge(x, y, NUDGE_FAST_MM))
        self.canvas.bind("<Escape>", lambda _e: self.select(None))

        status = ttk.Frame(parent)
        status.pack(fill="x", pady=(6, 0))
        self.fix_btn = icon_button(
            status, "Sorunları otomatik düzelt", "wand-magic-sparkles", self.fix_problems,
            a._icons, fill="#FFFFFF", style="Primary.TButton",
        )
        self.note_var = tk.StringVar()
        self.note_lbl = ttk.Label(status, textvariable=self.note_var, wraplength=560, justify="left")
        self.note_lbl.pack(side="left", fill="x", expand=True)
        ttk.Label(
            parent,
            text="Tıkla ve sürükle: taşı  ·  Ok tuşları: 0,5 mm (Shift: 2 mm)  ·  "
            "Çift tık: konumu sıfırla  ·  Ctrl/⌘+Z: geri al  ·  Kesikli çizgi: kenar boşluğu",
            style="Muted.TLabel",
        ).pack(fill="x", pady=(4, 0))
        self.select(None)

    # ── Seçim ────────────────────────────────────────────────────────

    def select(self, group: str | None) -> None:
        self.selected = group
        if group is None:
            self.sel_title.configure(text="Önizlemede bir öğeye tıklayın")
            for w in (self.sel_x, self.sel_y, *self.sel_align):
                w.state(["disabled"])
        else:
            self.sel_title.configure(text=ELEMENT_GROUPS[group])
            xv, yv = self.off_vars[group]
            self.sel_x.configure(textvariable=xv)
            self.sel_y.configure(textvariable=yv)
            for rb in self.sel_align:
                rb.configure(variable=self.align_vars[group])
            for w in (self.sel_x, self.sel_y, *self.sel_align):
                w.state(["!disabled"])
        self.refresh()

    def _hit(self, ex: int, ey: int) -> str | None:
        if self._layout is None:
            return None
        ox, oy = self._origin
        px, py = (ex - ox) / self._scale, (ey - oy) / self._scale
        tol = 4 / self._scale
        hits = [
            (abs((x1 - x0) * (y1 - y0)), g)
            for g, (x0, y0, x1, y1) in self._layout.group_boxes.items()
            if g in ELEMENT_GROUPS and x0 - tol <= px <= x1 + tol and y0 - tol <= py <= y1 + tol
        ]
        return min(hits)[1] if hits else None

    # ── Fare ve klavye ───────────────────────────────────────────────

    def _on_hover(self, event) -> None:
        if self._drag is None:
            self.canvas.configure(cursor="fleur" if self._hit(event.x, event.y) else "arrow")

    def _on_press(self, event) -> None:
        self.canvas.focus_set()
        group = self._hit(event.x, event.y)
        if group != self.selected:
            self.select(group)
        if group is None or self._layout is None:
            return
        self._drag = {
            "group": group,
            "x0": event.x,
            "y0": event.y,
            "start": list(self.app.element_offsets.get(group, [0.0, 0.0])),
            "box": self._layout.group_boxes[group],
            "pushed": False,
        }

    def _on_drag(self, event) -> None:
        d = self._drag
        if d is None or self._layout is None:
            return
        if not d["pushed"]:
            self._push_undo()
            d["pushed"] = True
        dpm = self._dpm()
        dx_dots = (event.x - d["x0"]) / self._scale
        dy_dots = (event.y - d["y0"]) / self._scale
        # Yatay ortaya yaslanma
        x0, _y0, x1, _y1 = d["box"]
        center = (x0 + x1) / 2 + dx_dots
        self._snapped = abs(center - self._layout.width / 2) < SNAP_MM * dpm
        if self._snapped:
            dx_dots = self._layout.width / 2 - (x0 + x1) / 2
        nx = round(d["start"][0] + dx_dots / dpm, 1)
        ny = round(d["start"][1] + dy_dots / dpm, 1)
        self._set_offset(d["group"], nx, ny, live=True)

    def _on_release(self, _event) -> None:
        if self._drag is not None and self._drag["pushed"]:
            self._snapped = False
            self.app._refresh_preview()
        self._drag = None
        self._snapped = False
        self.refresh()

    def _on_double(self, event) -> None:
        group = self._hit(event.x, event.y)
        if group:
            self.reset_group(group)

    def nudge(self, sx: int, sy: int, step: float) -> str:
        if self.selected:
            self._push_undo()
            dx, dy = self.app.element_offsets.get(self.selected, [0.0, 0.0])
            self._set_offset(self.selected, round(dx + sx * step, 1), round(dy + sy * step, 1))
        return "break"

    # ── Değer güncelleme ─────────────────────────────────────────────

    def _dpm(self) -> float:
        try:
            return dots_per_mm(int(float(self.app.dpi_var.get())))
        except (ValueError, tk.TclError):
            return dots_per_mm(203)

    def _set_offset(self, group: str, dx: float, dy: float, live: bool = False) -> None:
        if dx or dy:
            self.app.element_offsets[group] = [dx, dy]
        else:
            self.app.element_offsets.pop(group, None)
        xv, yv = self.off_vars[group]
        self._quiet = True
        try:
            xv.set(_fmt(dx))
            yv.set(_fmt(dy))
        finally:
            self._quiet = False
        if live:
            self.refresh(delay=10)  # sürüklerken yalnız bu önizleme
        else:
            self.app._refresh_preview()

    def _on_offset_var(self, group: str) -> None:
        if self._quiet:
            return
        xv, yv = self.off_vars[group]
        try:
            dx = float(xv.get().replace(",", ".") or 0)
            dy = float(yv.get().replace(",", ".") or 0)
        except ValueError:
            return  # yazım sürerken geçersiz değer: bekle
        if dx or dy:
            self.app.element_offsets[group] = [dx, dy]
        else:
            self.app.element_offsets.pop(group, None)
        self.app._refresh_preview()

    def _on_align(self, group: str) -> None:
        value = self.align_vars[group].get()
        if value == "center":
            self.app.element_align.pop(group, None)
        elif value in ALIGNMENTS:
            self.app.element_align[group] = value
        if not self._quiet:
            self.app._refresh_preview()

    def reset_group(self, group: str) -> None:
        self._push_undo()
        self._quiet = True
        self.align_vars[group].set("center")
        self._quiet = False
        self._set_offset(group, 0.0, 0.0)

    def reset_all(self) -> None:
        self._push_undo()
        self._quiet = True
        for group in ELEMENT_GROUPS:
            self.align_vars[group].set("center")
            xv, yv = self.off_vars[group]
            xv.set("0")
            yv.set("0")
        self._quiet = False
        self.app.element_offsets.clear()
        self.app.element_align.clear()
        self.app._refresh_preview()

    # ── Geri al / ön ayar ────────────────────────────────────────────

    def _snapshot(self) -> dict:
        return {
            "vars": {name: getattr(self.app, name).get() for name in TRACKED_VARS},
            "offsets": {k: list(v) for k, v in self.app.element_offsets.items()},
            "align": dict(self.app.element_align),
        }

    def _push_undo(self) -> None:
        self._undo.append(self._snapshot())
        del self._undo[:-50]

    def _restore(self, snap: dict) -> None:
        self._quiet = True
        try:
            for name, value in snap["vars"].items():
                getattr(self.app, name).set(value)
            self.app.element_offsets.clear()
            self.app.element_offsets.update({k: list(v) for k, v in snap["offsets"].items()})
            self.app.element_align.clear()
            self.app.element_align.update(snap["align"])
            for group in ELEMENT_GROUPS:
                self.align_vars[group].set(self.app.element_align.get(group, "center"))
                dx, dy = self.app.element_offsets.get(group, [0.0, 0.0])
                xv, yv = self.off_vars[group]
                xv.set(_fmt(dx))
                yv.set(_fmt(dy))
        finally:
            self._quiet = False
        self.app._refresh_preview()

    def undo(self) -> str:
        if self._undo:
            self._restore(self._undo.pop())
            self.note_var.set("Son değişiklik geri alındı.")
        return "break"

    def _apply(self, preset: dict) -> None:
        self._push_undo()
        snap = self._snapshot()
        snap["vars"].update(preset)
        snap["offsets"], snap["align"] = {}, {}
        self._restore(snap)

    # ── Otomatik düzeltme ────────────────────────────────────────────

    def _current_layout(self):
        return compute_layout(self.app.preview_label(), self.app.settings_from_ui())

    def fix_problems(self) -> None:
        """Etikete sığmayan içeriği adım adım düzeltir; yapılanları raporlar."""
        a = self.app
        try:
            layout = self._current_layout()
        except ValueError as exc:
            self.note_var.set(str(exc))
            return
        if not layout.overflow:
            self.note_var.set("✓ Düzeltilecek sorun yok.")
            return
        self._push_undo()
        done: list[str] = []

        def still() -> bool:
            return self._current_layout().overflow

        def num(var) -> float:
            return float(str(var.get()).replace(",", ".") or 0)

        if layout.out_of_bounds:
            for group in layout.out_of_bounds:
                self.align_vars[group].set("center")
                self._set_offset(group, 0.0, 0.0)
            done.append("taşan öğeler yerine alındı")
        if still() and not a.auto_fit_var.get():
            a.auto_fit_var.set(True)
            done.append("otomatik sığdırma açıldı")
        if still() and a.show_ak_var.get() and a.ak_pos_var.get() != "side":
            a.ak_pos_var.set("side")
            done.append("2. barkod yan yana alındı")
        if still():
            a.margin_var.set(_fmt(min(num(a.margin_var), 2.0)))
            for var in (a.gap_after_bc_var, a.gap_barcodes_var, a.gap_text_var):
                var.set(_fmt(round(num(var) * 0.5, 1)))
            done.append("kenar ve ara boşluklar azaltıldı")
        if still():
            for var in (a.font_barkod_var, a.font_ak_var, a.font_item_var):
                var.set(max(1, int(var.get()) - 1))
            if int(a.font_parca_var.get()) > 1:
                a.font_parca_var.set(int(a.font_parca_var.get()) - 1)
            done.append("yazılar bir kademe küçültüldü")
        if still():
            for var in (a.bc_height_var, a.ak_bc_height_var):
                var.set(_fmt(max(5.0, round(num(var) * 0.75, 1))))
            done.append("barkod yükseklikleri azaltıldı")

        ok = not still()
        summary = ", ".join(done) or "değişiklik yapılmadı"
        if ok:
            self.note_var.set(f"✓ Düzeltildi: {summary}. Beğenmezseniz Ctrl/⌘+Z ile geri alın.")
        else:
            self.note_var.set(
                f"Kısmen düzeltildi ({summary}). Kalan sorun için bazı alanları gizleyin "
                "ya da etiket ölçüsünü kontrol edin."
            )
        a._refresh_preview()
        self._note_locked = True  # bu mesaj bir sonraki çizimde silinmesin

    # ── Kaydet / kapat ───────────────────────────────────────────────

    def _save_close(self) -> None:
        self.app.persist_settings()
        self._close()

    def _close(self) -> None:
        self.app._layout_dialog = None
        self.destroy()

    # ── Önizleme ─────────────────────────────────────────────────────

    def refresh(self, delay: int = 60) -> None:
        if self._after is not None:
            self.after_cancel(self._after)
        self._after = self.after(delay, self._draw)

    def _draw(self) -> None:
        self._after = None
        if not self.winfo_exists():
            return
        cw = max(80, self.canvas.winfo_width())
        ch = max(80, self.canvas.winfo_height())
        self.canvas.delete("all")
        try:
            settings = self.app.settings_from_ui()
            label = self.app.preview_label()
            layout = compute_layout(label, settings)
        except ValueError as exc:
            self.note_var.set(str(exc))
            self.note_lbl.configure(foreground=ERR_RED)
            return
        photo, img = render_label_photoimage(
            label, settings, max_size=(cw - 24, ch - 24),
            highlight=self.selected, center_guide=self._snapped, layout=layout,
        )
        self._photo = photo
        self._layout = layout
        self._scale = img.width / max(1, layout.width)
        self._origin = ((cw - img.width) // 2, (ch - img.height) // 2)
        self.canvas.create_image(cw // 2, ch // 2, image=photo)
        mm_w, mm_h = settings.width_mm, settings.height_mm
        self.canvas.create_text(
            cw // 2, self._origin[1] + img.height + 6, anchor="n",
            text=f"{mm_w:g} × {mm_h:g} mm  ·  {settings.dpi} DPI", fill=MUTED,
        )

        if getattr(self, "_note_locked", False):
            self._note_locked = False
        elif layout.overflow:
            self.note_var.set(layout.fit_note or "İçerik etikete sığmıyor.")
        else:
            self.note_var.set(
                "✓ Tüm öğeler etikete sığıyor."
                + (f"  ({layout.fit_note})" if layout.fit_note else "")
            )
        self.note_lbl.configure(foreground=ERR_RED if layout.overflow else OK_GREEN)
        if layout.overflow:
            self.fix_btn.pack(side="right", padx=(8, 0))
        else:
            self.fix_btn.pack_forget()


def _fmt(value: float) -> str:
    """Spinbox için kısa sayı: 2.0 → "2", 1.25 → "1.25"."""
    return f"{float(value):g}"

