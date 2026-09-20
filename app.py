"""
BYK Seri Baskı Pro — Biyik.dev

Excel'deki Barkod / A-K Barkod / ItemNo / ParcaAd satırlarını okuyup
TSPL ile termal etikete basar.

Çalıştırma:
    Windows : BASLAT.bat   |  python app.py
    macOS   : ./BASLAT.sh  |  python3 app.py

Paketleme:
    Windows : BUILD_RELEASE.bat  →  Kurulum.exe zip
    macOS   : ./BUILD_RELEASE_MAC.sh  →  .app zip
"""

from __future__ import annotations

import json
import sys
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from about_dialog import open_about
from app_icon import apply_app_icon
from branding import APP_DISPLAY, APP_TITLE
from excel_loader import ColumnHeaders, load_labels_from_excel
from help_dialog import open_help
from label_preview import render_label_photoimage
from paths import app_home, assets_dir, resource_dir
from printer_raw import default_printer, list_printers, send_raw
from serial_dialog import open_serial_dialog
from splash import show_splash
from tspl_builder import (
    BARCODE_TYPES,
    BRAND_POSITIONS,
    FONT_SIZE_LABELS,
    LabelData,
    LabelSettings,
    build_batch_tspl,
    build_tspl,
    describe_layout,
    normalize_barcode_type,
)
from ui_icons import (
    C_GOLD,
    C_GREEN,
    C_MUTED,
    C_NAVY,
    C_TEAL,
    IconStore,
    icon_button,
    icon_labelframe,
)

APP_DIR = app_home()
CONFIG_PATH = APP_DIR / "config.json"
CONTACT_EMAIL = "metin@biyik.dev"

# Test baskı örnek şablonu (geliştirici bilgileri)
TEST_SAMPLE_LABEL = LabelData(
    barkod="metin@biyik.dev",
    ak_barkod="+90 (540) 461 35 43",
    item_no="Metin Faruk Bıyık tarafından geliştirilmiştir.",
    parca_ad="İletişime geçebilirsiniz.",
)
TEST_SAMPLE_FONT = 2  # Orta
TEST_SAMPLE_BRAND = "BYK PROJECT"
TEST_SAMPLE_BRAND_POS = "top"


def load_config() -> dict:
    _ensure_user_files()
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(cfg: dict) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def _ensure_user_files() -> None:
    """Exe kurulumunda varsayılan config/excel'i yazılabilir klasöre kopyala."""
    import shutil

    APP_DIR.mkdir(parents=True, exist_ok=True)
    for name in ("config.json", "Barkod.xlsx"):
        dest = APP_DIR / name
        if dest.exists():
            continue
        src = resource_dir() / name
        if src.exists():
            try:
                shutil.copy2(src, dest)
            except OSError:
                pass


def default_excel_path() -> Path:
    _ensure_user_files()
    for name in ("Barkod.xlsx", "Kitap1.xlsx"):
        p = APP_DIR / name
        if p.exists():
            return p
    return APP_DIR / "Barkod.xlsx"


def _legacy_font(cfg: dict, key: str, default: int) -> int:
    if key in cfg:
        return int(cfg[key])
    # Eski tek font_size varsa ItemNo için kullan
    if "font_size" in cfg and key == "font_item":
        return int(cfg["font_size"])
    return default


def settings_from_config(cfg: dict, **overrides) -> LabelSettings:
    return LabelSettings(
        width_mm=float(overrides.get("width_mm", cfg.get("label_width_mm", 98))),
        height_mm=float(overrides.get("height_mm", cfg.get("label_height_mm", 98))),
        gap_mm=float(overrides.get("gap_mm", cfg.get("gap_mm", 3))),
        dpi=int(cfg.get("dpi", 203)),
        copies=int(overrides.get("copies", cfg.get("copies", 1))),
        density=int(overrides.get("density", cfg.get("density", 8))),
        speed=int(cfg.get("speed", 4)),
        direction=int(cfg.get("direction", 1)),
        barcode_type=str(
            overrides.get(
                "barcode_type",
                normalize_barcode_type(cfg.get("barcode_type", "128")),
            )
        ),
        ak_barcode_type=str(
            overrides.get(
                "ak_barcode_type",
                normalize_barcode_type(
                    cfg.get("ak_barcode_type", cfg.get("barcode_type", "128"))
                ),
            )
        ),
        barcode_height_mm=float(
            overrides.get("barcode_height_mm", cfg.get("barcode_height_mm", 20))
        ),
        ak_barcode_height_mm=float(
            overrides.get("ak_barcode_height_mm", cfg.get("ak_barcode_height_mm", 14))
        ),
        barcode_narrow=int(cfg.get("barcode_narrow", 3)),
        barcode_wide=int(cfg.get("barcode_wide", 6)),
        qr_ecc=str(overrides.get("qr_ecc", cfg.get("qr_ecc", "M"))),
        qr_cell=int(overrides.get("qr_cell", cfg.get("qr_cell", 4))),
        font_barkod=int(overrides.get("font_barkod", _legacy_font(cfg, "font_barkod", 2))),
        font_ak=int(overrides.get("font_ak", _legacy_font(cfg, "font_ak", 2))),
        font_item=int(overrides.get("font_item", _legacy_font(cfg, "font_item", 3))),
        font_brand=int(overrides.get("font_brand", cfg.get("font_brand", 1))),
        brand_text=str(overrides.get("brand_text", cfg.get("brand_text", ""))),
        brand_position=str(
            overrides.get("brand_position", cfg.get("brand_position", "bottom"))
        ),
        gap_after_barcode_mm=float(cfg.get("gap_after_barcode_mm", 1.5)),
        gap_after_text_mm=float(
            cfg.get("gap_after_text_mm", cfg.get("gap_between_lines_mm", 2.5))
        ),
        gap_between_barcodes_mm=float(cfg.get("gap_between_barcodes_mm", 4)),
        margin_mm=float(cfg.get("margin_mm", 6)),
    )


def _font_combo_values() -> list[str]:
    return [f"{k} — {v}" for k, v in FONT_SIZE_LABELS.items()]


def _parse_font_combo(raw: str, default: int = 2) -> int:
    digits = "".join(ch for ch in (raw or "").split()[0] if ch.isdigit())
    try:
        return max(1, min(4, int(digits))) if digits else default
    except ValueError:
        return default


class LabelApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        apply_app_icon(self)
        self.geometry("1120x820")
        self.minsize(960, 640)
        self.configure(bg="#F3F5F7")

        self.cfg = load_config()
        self.labels: list[LabelData] = []
        self.column_headers = ColumnHeaders.from_dict(self.cfg.get("excel_columns"))
        self._preview_photo = None
        self._header_photos: list = []
        self._icons = IconStore()
        self._current_label: LabelData | None = None
        self._preview_resize_after: str | None = None
        self._preview_size: tuple[int, int] = (0, 0)

        self.excel_path = tk.StringVar(value=str(default_excel_path()))
        self.printer_var = tk.StringVar()
        self.width_var = tk.StringVar(value=str(self.cfg.get("label_width_mm", 98)))
        self.height_var = tk.StringVar(value=str(self.cfg.get("label_height_mm", 98)))
        self.gap_var = tk.StringVar(value=str(self.cfg.get("gap_mm", 3)))
        self.copies_var = tk.StringVar(value=str(self.cfg.get("copies", 1)))
        self.density_var = tk.StringVar(value=str(self.cfg.get("density", 8)))
        self.bc_height_var = tk.StringVar(
            value=str(self.cfg.get("barcode_height_mm", 20))
        )
        self.ak_bc_height_var = tk.StringVar(
            value=str(self.cfg.get("ak_barcode_height_mm", 14))
        )

        fb = _legacy_font(self.cfg, "font_barkod", 2)
        fa = _legacy_font(self.cfg, "font_ak", 2)
        fi = _legacy_font(self.cfg, "font_item", 3)
        self.font_barkod_var = tk.IntVar(value=fb)
        self.font_ak_var = tk.IntVar(value=fa)
        self.font_item_var = tk.IntVar(value=fi)

        self.brand_text_var = tk.StringVar(value=str(self.cfg.get("brand_text", "")))
        self.brand_pos_var = tk.StringVar(
            value=str(self.cfg.get("brand_position", "bottom"))
        )
        self.barcode_type_var = tk.StringVar(
            value=normalize_barcode_type(self.cfg.get("barcode_type", "128"))
        )
        self.ak_barcode_type_var = tk.StringVar(
            value=normalize_barcode_type(
                self.cfg.get("ak_barcode_type", self.cfg.get("barcode_type", "128"))
            )
        )
        self.status_var = tk.StringVar(value="Excel dosyasını yükleyin.")

        self._build_ui()
        self._load_printers()
        # İlk layout oturduktan sonra yükle — önizleme gerçek tuval boyutuna sığsın
        if Path(self.excel_path.get()).exists():
            self.after_idle(self.load_excel)

    def _make_font_combo(self, parent, var: tk.IntVar, row: int, col: int) -> ttk.Combobox:
        combo = ttk.Combobox(
            parent,
            values=_font_combo_values(),
            state="readonly",
            width=14,
        )
        cur = int(var.get())
        combo.set(f"{cur} — {FONT_SIZE_LABELS.get(cur, 'Orta')}")
        combo.grid(row=row, column=col, sticky="w", padx=4, pady=2)

        def on_change(_e=None, v=var, c=combo) -> None:
            v.set(_parse_font_combo(c.get(), int(v.get())))
            self._refresh_preview()

        combo.bind("<<ComboboxSelected>>", on_change)
        return combo

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}

        # Soft kurumsal üst şerit
        header = tk.Frame(self, bg="#FFFFFF", highlightthickness=0)
        header.pack(side="top", fill="x")
        head_inner = tk.Frame(header, bg="#FFFFFF")
        head_inner.pack(fill="x", padx=14, pady=10)

        badge_path = assets_dir() / "biyik_badge.png"
        if badge_path.exists():
            try:
                from PIL import Image, ImageTk

                img = Image.open(badge_path).convert("RGBA").resize(
                    (40, 40), Image.Resampling.LANCZOS
                )
                photo = ImageTk.PhotoImage(img)
                self._header_photos.append(photo)
                tk.Label(head_inner, image=photo, bg="#FFFFFF").pack(
                    side="left", padx=(0, 10)
                )
            except Exception:
                pass

        titles = tk.Frame(head_inner, bg="#FFFFFF")
        titles.pack(side="left")
        title_row = tk.Frame(titles, bg="#FFFFFF")
        title_row.pack(anchor="w")
        barcode_ic = self._icons.get("barcode", size=16, fill=C_NAVY)
        if barcode_ic is not None:
            tk.Label(title_row, image=barcode_ic, bg="#FFFFFF").pack(
                side="left", padx=(0, 6)
            )
        tk.Label(
            title_row,
            text=APP_DISPLAY,
            font=("Segoe UI Semibold", 12),
            fg="#1B3352",
            bg="#FFFFFF",
        ).pack(side="left")
        tk.Label(
            titles,
            text="Biyik.dev",
            font=("Segoe UI Semibold", 10),
            fg="#B8962E",
            bg="#FFFFFF",
        ).pack(anchor="w")

        tk.Frame(self, bg="#E6E9EE", height=1).pack(side="top", fill="x")

        credit = ttk.Frame(self)
        credit.pack(side="bottom", fill="x", padx=10, pady=(2, 8))
        mail_ic = self._icons.get("envelope", size=12, fill=C_NAVY)
        if mail_ic is not None:
            ttk.Label(credit, image=mail_ic).pack(side="left", padx=(0, 4))
        ttk.Label(
            credit,
            text="BIYIK.DEV tarafından geliştirilmiştir  ·  İletişim:",
        ).pack(side="left")
        mail = ttk.Label(credit, text=CONTACT_EMAIL, foreground="#0B57D0", cursor="hand2")
        mail.pack(side="left", padx=(4, 0))
        mail.bind("<Button-1>", lambda _e: self._open_mail())

        actions = ttk.Frame(self)
        actions.pack(side="bottom", fill="x", padx=10, pady=(4, 2))
        icon_button(
            actions,
            "Test Baskı (örnek)",
            "flask",
            self.print_test,
            self._icons,
            fill=C_GOLD,
        ).pack(side="left", padx=4)
        icon_button(
            actions,
            "Seçilileri Bas",
            "print",
            self.print_selected,
            self._icons,
            fill=C_TEAL,
        ).pack(side="left", padx=4)
        icon_button(
            actions,
            "Tümünü Bas",
            "layer-group",
            self.print_all,
            self._icons,
            fill=C_GREEN,
        ).pack(side="left", padx=4)
        icon_button(
            actions,
            "Ayarları Kaydet",
            "floppy-disk",
            self.persist_settings,
            self._icons,
        ).pack(side="left", padx=4)
        icon_button(
            actions,
            "Kullanım",
            "book-open",
            self.show_help,
            self._icons,
            fill=C_GOLD,
        ).pack(side="left", padx=4)
        icon_button(
            actions,
            "Hakkında",
            "circle-info",
            self.show_about,
            self._icons,
        ).pack(side="left", padx=4)
        ttk.Label(actions, textvariable=self.status_var).pack(side="right", padx=8)

        top = icon_labelframe(
            self, "Kaynak / Yazıcı", "hard-drive", self._icons, fill=C_NAVY
        )
        top.pack(side="top", fill="x", padx=10, pady=(8, 4))

        excel_ic = self._icons.get("file-excel", size=13, fill=C_GREEN)
        excel_lbl = ttk.Frame(top)
        if excel_ic is not None:
            ttk.Label(excel_lbl, image=excel_ic).pack(side="left", padx=(0, 4))
        ttk.Label(excel_lbl, text="Excel:").pack(side="left")
        excel_lbl.grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(top, textvariable=self.excel_path, width=70).grid(
            row=0, column=1, sticky="ew", **pad
        )
        icon_button(
            top, "Seç…", "folder-open", self.browse_excel, self._icons, fill=C_GOLD
        ).grid(row=0, column=2, **pad)
        icon_button(
            top, "Yükle", "file-arrow-up", self.load_excel, self._icons, fill=C_GREEN
        ).grid(row=0, column=3, **pad)
        icon_button(
            top,
            "Seri Üret…",
            "wand-magic-sparkles",
            self.open_serial,
            self._icons,
            fill=C_GOLD,
        ).grid(row=0, column=4, **pad)

        print_ic = self._icons.get("print", size=13, fill=C_NAVY)
        print_lbl = ttk.Frame(top)
        if print_ic is not None:
            ttk.Label(print_lbl, image=print_ic).pack(side="left", padx=(0, 4))
        ttk.Label(print_lbl, text="Yazıcı:").pack(side="left")
        print_lbl.grid(row=1, column=0, sticky="w", **pad)
        self.printer_combo = ttk.Combobox(
            top, textvariable=self.printer_var, width=67, state="readonly"
        )
        self.printer_combo.grid(row=1, column=1, sticky="ew", **pad)
        icon_button(
            top, "Yenile", "arrows-rotate", self._load_printers, self._icons
        ).grid(row=1, column=2, **pad)
        top.columnconfigure(1, weight=1)

        settings = icon_labelframe(
            self, "Etiket / Baskı ayarları", "sliders", self._icons, fill=C_NAVY
        )
        settings.pack(side="top", fill="x", padx=10, pady=4)

        for col, (label, var) in enumerate(
            [
                ("Genişlik (mm)", self.width_var),
                ("Yükseklik (mm)", self.height_var),
                ("Gap", self.gap_var),
                ("Kopya", self.copies_var),
                ("Yoğunluk", self.density_var),
            ]
        ):
            ttk.Label(settings, text=label).grid(row=0, column=col * 2, sticky="e", **pad)
            entry = ttk.Entry(settings, textvariable=var, width=7)
            entry.grid(row=0, column=col * 2 + 1, sticky="w", **pad)
            var.trace_add("write", lambda *_: self._refresh_preview())

        ttk.Label(settings, text="Ana barkod yük. (mm)").grid(
            row=1, column=0, sticky="e", **pad
        )
        e1 = ttk.Entry(settings, textvariable=self.bc_height_var, width=7)
        e1.grid(row=1, column=1, sticky="w", **pad)
        self.bc_height_var.trace_add("write", lambda *_: self._refresh_preview())

        self.lbl_ak_height = ttk.Label(settings, text="2. barkod yük. (mm)")
        self.lbl_ak_height.grid(row=1, column=2, sticky="e", **pad)
        e2 = ttk.Entry(settings, textvariable=self.ak_bc_height_var, width=7)
        e2.grid(row=1, column=3, sticky="w", **pad)
        self.ak_bc_height_var.trace_add("write", lambda *_: self._refresh_preview())

        type_values = [f"{k} — {v}" for k, v in BARCODE_TYPES.items()]
        ttk.Label(settings, text="Ana barkod tipi:").grid(
            row=2, column=0, sticky="e", **pad
        )
        self.bc_type_combo = ttk.Combobox(
            settings, values=type_values, state="readonly", width=16
        )
        cur_bc = self.barcode_type_var.get()
        self.bc_type_combo.set(f"{cur_bc} — {BARCODE_TYPES.get(cur_bc, cur_bc)}")
        self.bc_type_combo.grid(row=2, column=1, sticky="w", **pad)
        self.bc_type_combo.bind("<<ComboboxSelected>>", self._on_bc_type_change)

        ttk.Label(settings, text="2. barkod tipi:").grid(
            row=2, column=2, sticky="e", **pad
        )
        self.ak_type_combo = ttk.Combobox(
            settings, values=type_values, state="readonly", width=16
        )
        cur_ak = self.ak_barcode_type_var.get()
        self.ak_type_combo.set(f"{cur_ak} — {BARCODE_TYPES.get(cur_ak, cur_ak)}")
        self.ak_type_combo.grid(row=2, column=3, sticky="w", **pad)
        self.ak_type_combo.bind("<<ComboboxSelected>>", self._on_ak_type_change)

        ttk.Label(
            settings,
            text="QR seçiliyse yükseklik alanı kare kenar (mm) olarak kullanılır.",
        ).grid(row=2, column=4, columnspan=4, sticky="w", **pad)

        # Font satırı — ayrı kontroller
        fonts = icon_labelframe(
            self, "Baskı fontları (ayrı ayar)", "font", self._icons, fill=C_NAVY
        )
        fonts.pack(side="top", fill="x", padx=10, pady=4)

        self.lbl_font_barkod = ttk.Label(fonts, text="Barkod metni:")
        self.lbl_font_barkod.grid(row=0, column=0, sticky="e", **pad)
        self._make_font_combo(fonts, self.font_barkod_var, 0, 1)

        self.lbl_font_ak = ttk.Label(fonts, text="A-K Barkod metni:")
        self.lbl_font_ak.grid(row=0, column=2, sticky="e", **pad)
        self._make_font_combo(fonts, self.font_ak_var, 0, 3)

        self.lbl_font_item = ttk.Label(fonts, text="ItemNo / ParcaAd:")
        self.lbl_font_item.grid(row=0, column=4, sticky="e", **pad)
        self._make_font_combo(fonts, self.font_item_var, 0, 5)

        # Markalama
        brand = icon_labelframe(
            self,
            "Markalama (her etikete damga — örn. BYK Project)",
            "stamp",
            self._icons,
            fill=C_GOLD,
        )
        brand.pack(side="top", fill="x", padx=10, pady=4)

        ttk.Label(brand, text="Marka metni:").grid(row=0, column=0, sticky="e", **pad)
        brand_entry = ttk.Entry(brand, textvariable=self.brand_text_var, width=28)
        brand_entry.grid(row=0, column=1, sticky="w", **pad)
        self.brand_text_var.trace_add("write", lambda *_: self._refresh_preview())

        ttk.Label(brand, text="Konum:").grid(row=0, column=2, sticky="e", **pad)
        pos_values = [f"{k} — {v}" for k, v in BRAND_POSITIONS.items()]
        self.brand_pos_combo = ttk.Combobox(
            brand, values=pos_values, state="readonly", width=12
        )
        cur_pos = self.brand_pos_var.get()
        self.brand_pos_combo.set(
            f"{cur_pos} — {BRAND_POSITIONS.get(cur_pos, 'Alt')}"
        )
        self.brand_pos_combo.grid(row=0, column=3, sticky="w", **pad)
        self.brand_pos_combo.bind("<<ComboboxSelected>>", self._on_brand_pos_change)

        ttk.Label(
            brand,
            text="Boş bırakılırsa damga basılmaz. Üst veya alt kenara ortalı yazılır.",
        ).grid(row=0, column=4, columnspan=2, sticky="w", **pad)

        body = ttk.Frame(self)
        body.pack(side="top", fill="both", expand=True, padx=10, pady=(4, 4))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=0, minsize=260)
        body.rowconfigure(0, weight=1)

        self.list_frame = icon_labelframe(
            body,
            "Etiket listesi — Barkod → (A-K) → ItemNo → ParcaAd  (+ Marka)",
            "table-list",
            self._icons,
            fill=C_NAVY,
        )
        self.list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        # Liste arama / filtre + liste temizle
        filter_bar = ttk.Frame(self.list_frame)
        filter_bar.pack(fill="x", padx=8, pady=(8, 0))
        search_ic = self._icons.get("magnifying-glass", size=12, fill=C_NAVY)
        if search_ic is not None:
            ttk.Label(filter_bar, image=search_ic).pack(side="left", padx=(0, 4))
        ttk.Label(filter_bar, text="Ara:").pack(side="left")
        self.filter_var = tk.StringVar()
        self.filter_entry = ttk.Entry(filter_bar, textvariable=self.filter_var)
        self.filter_entry.pack(side="left", fill="x", expand=True, padx=6)
        self.filter_var.trace_add("write", lambda *_: self._rebuild_tree())
        icon_button(
            filter_bar,
            "Filtreyi temizle",
            "xmark",
            self._clear_filter,
            self._icons,
            size=12,
            fill=C_NAVY,
        ).pack(side="left", padx=(0, 4))
        icon_button(
            filter_bar,
            "Listeyi temizle",
            "trash-can",
            self._clear_labels,
            self._icons,
            size=12,
            fill=C_MUTED,
        ).pack(side="left")

        cols = ("barkod", "ak", "item", "parca")
        tree_wrap = ttk.Frame(self.list_frame)
        tree_wrap.pack(side="top", fill="both", expand=True, padx=8, pady=8)
        self.tree = ttk.Treeview(
            tree_wrap, columns=cols, show="headings", selectmode="extended"
        )
        self.tree.heading("barkod", text="Barkod")
        self.tree.heading("ak", text="A-K Barkod")
        self.tree.heading("item", text="ItemNo")
        self.tree.heading("parca", text="ParcaAd")
        self.tree.column("barkod", width=160)
        self.tree.column("ak", width=120)
        self.tree.column("item", width=120)
        self.tree.column("parca", width=160)
        scroll = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self._apply_column_headers(self.column_headers)

        right = icon_labelframe(body, "Önizleme", "eye", self._icons, fill=C_TEAL)
        right.grid(row=0, column=1, sticky="nsew")

        tabs = ttk.Notebook(right)
        tabs.pack(fill="both", expand=True, padx=6, pady=6)

        tab_visual = ttk.Frame(tabs)
        tab_tspl = ttk.Frame(tabs)
        img_visual = self._icons.get("image", size=12, fill=C_NAVY)
        img_tspl = self._icons.get("code", size=12, fill=C_NAVY)
        if img_visual is not None:
            tabs.add(tab_visual, text=" Görsel", image=img_visual, compound="left")
        else:
            tabs.add(tab_visual, text="Görsel")
        if img_tspl is not None:
            tabs.add(tab_tspl, text=" TSPL", image=img_tspl, compound="left")
        else:
            tabs.add(tab_tspl, text="TSPL")

        # Başlangıç boyutu yalnızca ilk layout için; sonra alanla ölçeklenir
        self.preview_canvas = tk.Canvas(
            tab_visual, width=260, height=220, bg="#F0F0F0", highlightthickness=0
        )
        self.preview_canvas.pack(fill="both", expand=True, padx=6, pady=6)
        self.preview_canvas.bind("<Configure>", self._on_preview_configure)

        self.preview_text = tk.Text(
            tab_tspl, width=36, height=12, font=("Consolas", 8), wrap="none"
        )
        self.preview_text.pack(fill="both", expand=True, padx=6, pady=6)

    def _clear_labels(self) -> None:
        """Etiket listesini tamamen boşaltır."""
        if not self.labels:
            self.status_var.set("Liste zaten boş.")
            return
        count = len(self.labels)
        if not messagebox.askyesno(
            "Listeyi temizle",
            f"{count} etiket listeden silinecek.\nDevam edilsin mi?",
            parent=self,
        ):
            return
        self.labels = []
        self.filter_var.set("")
        self._current_label = None
        self._rebuild_tree()
        self.preview_canvas.delete("all")
        self.preview_text.delete("1.0", "end")
        self._preview_photo = None
        self.status_var.set("Etiket listesi temizlendi.")

    def _on_brand_pos_change(self, _event=None) -> None:
        raw = (self.brand_pos_combo.get() or "bottom").split("—", 1)[0].strip().lower()
        if raw not in BRAND_POSITIONS:
            raw = "bottom"
        self.brand_pos_var.set(raw)
        self._refresh_preview()

    def _on_bc_type_change(self, _event=None) -> None:
        raw = (self.bc_type_combo.get() or "128").split("—", 1)[0].strip()
        self.barcode_type_var.set(normalize_barcode_type(raw))
        self._refresh_preview()

    def _on_ak_type_change(self, _event=None) -> None:
        raw = (self.ak_type_combo.get() or "128").split("—", 1)[0].strip()
        self.ak_barcode_type_var.set(normalize_barcode_type(raw))
        self._refresh_preview()

    def open_serial(self) -> None:
        outcome = open_serial_dialog(self)
        if not outcome:
            return
        labels, mode = outcome
        if mode == "append":
            self.labels.extend(labels)
        else:
            self.labels = list(labels)
            # Seri üretimde Excel başlıkları yoksa varsayılanları koru
        self.filter_var.set("")
        self._rebuild_tree()
        self.status_var.set(f"Seri üretim: {len(labels)} etiket ({mode})")
        if self.tree.get_children():
            first = self.tree.get_children()[0]
            self.tree.selection_set(first)
            self.tree.focus(first)
            self._show_preview(self.labels[int(first)])

    def _open_mail(self) -> None:
        webbrowser.open(f"mailto:{CONTACT_EMAIL}")

    def show_about(self) -> None:
        open_about(self, APP_TITLE)

    def show_help(self) -> None:
        open_help(self, APP_TITLE)

    def _load_printers(self) -> None:
        try:
            printers = list_printers()
        except Exception as exc:
            messagebox.showwarning("Yazıcı", str(exc))
            printers = []

        self.printer_combo["values"] = printers
        saved = self.cfg.get("printer_name") or ""
        if saved and saved in printers:
            self.printer_var.set(saved)
        elif printers:
            try:
                d = default_printer()
                self.printer_var.set(d if d in printers else printers[0])
            except Exception:
                self.printer_var.set(printers[0])

    def browse_excel(self) -> None:
        path = filedialog.askopenfilename(
            title="Excel seç",
            filetypes=[("Excel", "*.xlsx *.xlsm *.xls"), ("Tümü", "*.*")],
            initialdir=str(APP_DIR),
        )
        if path:
            self.excel_path.set(path)
            self.load_excel()

    def _apply_column_headers(self, headers: ColumnHeaders) -> None:
        """Liste, font ve ayar etiketlerini Excel 1. satır adlarına göre güncelle."""
        self.column_headers = headers
        h = headers

        self.tree.heading("barkod", text=h.barkod)
        self.tree.heading("ak", text=h.ak_barkod)
        self.tree.heading("item", text=h.item_no)
        self.tree.heading("parca", text=h.parca_ad)

        title = (
            f"Etiket listesi — {h.barkod} → ({h.ak_barkod}) → "
            f"{h.item_no} → {h.parca_ad}  (+ Marka)"
        )
        try:
            self.list_frame.title_label.configure(text=title)  # type: ignore[attr-defined]
        except Exception:
            pass

        self.lbl_font_barkod.configure(text=f"{h.barkod} metni:")
        self.lbl_font_ak.configure(text=f"{h.ak_barkod} metni:")
        self.lbl_font_item.configure(text=f"{h.item_no} / {h.parca_ad}:")
        self.lbl_ak_height.configure(text=f"{h.ak_barkod} yük. (mm)")

    def load_excel(self) -> None:
        path = Path(self.excel_path.get())
        cols = self.cfg.get("excel_columns", {})
        try:
            result = load_labels_from_excel(
                path,
                col_barkod=cols.get("barkod", "Barkod"),
                col_ak=cols.get("ak_barkod", "A-K Barkod"),
                col_item=cols.get("item_no", "ItemNo"),
                col_parca=cols.get("parca_ad", "ParcaAd"),
            )
        except Exception as exc:
            messagebox.showerror("Excel", f"Okuma hatası:\n{exc}")
            return

        self.labels = result.labels
        self._apply_column_headers(result.headers)
        self.cfg["excel_columns"] = result.headers.as_dict()
        self._rebuild_tree()

        total = len(self.labels)
        shown = len(self.tree.get_children())
        self.status_var.set(
            f"{total} etiket yüklendi"
            + (f"  ·  gösterilen: {shown}" if shown != total else "")
            + f"  ·  Sütunlar: {result.headers.barkod} / {result.headers.ak_barkod} / "
            f"{result.headers.item_no} / {result.headers.parca_ad}"
        )
        if self.labels and self.tree.get_children():
            first = self.tree.get_children()[0]
            self.tree.selection_set(first)
            self.tree.focus(first)
            self._show_preview(self.labels[int(first)])

    def _clear_filter(self) -> None:
        self.filter_var.set("")

    def _rebuild_tree(self) -> None:
        """Listeyi (ve ara filtresini) yeniden doldur; iid = etiket indeksi."""
        query = ""
        if getattr(self, "filter_var", None) is not None:
            query = (self.filter_var.get() or "").strip().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)

        for idx, lab in enumerate(self.labels):
            hay = " ".join(
                (lab.barkod, lab.ak_barkod, lab.item_no, lab.parca_ad)
            ).lower()
            if query and query not in hay:
                continue
            self.tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(lab.barkod, lab.ak_barkod, lab.item_no, lab.parca_ad),
            )

        if query:
            shown = len(self.tree.get_children())
            self.status_var.set(
                f"Filtre: “{query}”  ·  {shown} / {len(self.labels)} satır"
            )

    def settings_from_ui(self) -> LabelSettings:
        try:
            return settings_from_config(
                self.cfg,
                width_mm=float(self.width_var.get().replace(",", ".")),
                height_mm=float(self.height_var.get().replace(",", ".")),
                gap_mm=float(self.gap_var.get().replace(",", ".")),
                copies=max(1, int(self.copies_var.get())),
                density=int(self.density_var.get()),
                barcode_height_mm=float(self.bc_height_var.get().replace(",", ".")),
                ak_barcode_height_mm=float(
                    self.ak_bc_height_var.get().replace(",", ".")
                ),
                font_barkod=int(self.font_barkod_var.get()),
                font_ak=int(self.font_ak_var.get()),
                font_item=int(self.font_item_var.get()),
                brand_text=self.brand_text_var.get().strip(),
                brand_position=self.brand_pos_var.get().strip() or "bottom",
                barcode_type=normalize_barcode_type(self.barcode_type_var.get()),
                ak_barcode_type=normalize_barcode_type(self.ak_barcode_type_var.get()),
            )
        except ValueError as exc:
            raise ValueError("Boyut / font / kopya alanları sayı olmalı.") from exc

    def persist_settings(self) -> None:
        try:
            s = self.settings_from_ui()
        except ValueError as exc:
            messagebox.showerror("Ayar", str(exc))
            return
        self.cfg.update(
            {
                "printer_name": self.printer_var.get(),
                "label_width_mm": s.width_mm,
                "label_height_mm": s.height_mm,
                "gap_mm": s.gap_mm,
                "copies": s.copies,
                "density": s.density,
                "barcode_height_mm": s.barcode_height_mm,
                "ak_barcode_height_mm": s.ak_barcode_height_mm,
                "font_barkod": s.font_barkod,
                "font_ak": s.font_ak,
                "font_item": s.font_item,
                "font_brand": s.font_brand,
                "brand_text": s.brand_text,
                "brand_position": s.brand_position,
                "barcode_type": s.barcode_type,
                "ak_barcode_type": s.ak_barcode_type,
                "qr_ecc": s.qr_ecc,
                "qr_cell": s.qr_cell,
                "barcode_narrow": s.barcode_narrow,
                "barcode_wide": s.barcode_wide,
                "gap_after_barcode_mm": s.gap_after_barcode_mm,
                "gap_after_text_mm": s.gap_after_text_mm,
                "gap_between_barcodes_mm": s.gap_between_barcodes_mm,
                "margin_mm": s.margin_mm,
                "excel_columns": self.column_headers.as_dict(),
            }
        )
        save_config(self.cfg)
        self.status_var.set("Ayarlar kaydedildi.")

    def _on_select(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        try:
            idx = int(sel[0])
        except ValueError:
            idx = self.tree.index(sel[0])
        if 0 <= idx < len(self.labels):
            self._show_preview(self.labels[idx])

    def _preview_canvas_size(self) -> tuple[int, int]:
        """Önizleme tuvalinin kullanılabilir boyutu (henüz çizilmediyse makul varsayılan)."""
        self.update_idletasks()
        cw = int(self.preview_canvas.winfo_width())
        ch = int(self.preview_canvas.winfo_height())
        if cw < 40:
            try:
                cw = int(self.preview_canvas.cget("width"))
            except Exception:
                cw = 260
        if ch < 40:
            try:
                ch = int(self.preview_canvas.cget("height"))
            except Exception:
                ch = 220
        return max(80, cw), max(80, ch)

    def _on_preview_configure(self, event: tk.Event) -> None:
        """Pencere / panel boyutu değişince önizlemeyi alana sığdır."""
        if event.widget is not self.preview_canvas:
            return
        new_size = (int(event.width), int(event.height))
        if new_size[0] < 40 or new_size[1] < 40:
            return
        if new_size == self._preview_size:
            return
        self._preview_size = new_size
        if self._preview_resize_after is not None:
            try:
                self.after_cancel(self._preview_resize_after)
            except Exception:
                pass
        self._preview_resize_after = self.after(60, self._refresh_preview)

    def _refresh_preview(self) -> None:
        if self._current_label is not None:
            self._show_preview(self._current_label)

    def _show_preview(self, label: LabelData) -> None:
        self._current_label = label
        try:
            settings = self.settings_from_ui()
        except ValueError:
            return

        cw, ch = self._preview_canvas_size()
        # Kenar boşluğu bırak; kısa kenara göre ölçekle
        max_side = max(64, min(cw, ch) - 12)

        self.preview_canvas.delete("all")
        try:
            photo, _ = render_label_photoimage(label, settings, max_side=max_side)
            self._preview_photo = photo
            self.preview_canvas.create_image(cw // 2, ch // 2, image=photo)
        except Exception as exc:
            self.preview_canvas.create_text(
                cw // 2,
                ch // 2,
                text=f"Önizleme hatası:\n{exc}",
                fill="red",
                justify="center",
                width=max(80, cw - 20),
            )

        summary = describe_layout(label, settings)
        cmd = build_tspl(label, settings)
        text = (
            f"{settings.width_mm:g}×{settings.height_mm:g} mm\n"
            f"{'─' * 40}\n"
            f"{summary}\n"
            f"{'─' * 40}\n"
            f"{cmd}"
        )
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", text)

    def _visible_labels(self) -> list[LabelData]:
        result: list[LabelData] = []
        for item_id in self.tree.get_children():
            try:
                idx = int(item_id)
            except ValueError:
                idx = self.tree.index(item_id)
            if 0 <= idx < len(self.labels):
                result.append(self.labels[idx])
        return result

    def _selected_labels(self) -> list[LabelData]:
        result: list[LabelData] = []
        for item_id in self.tree.selection():
            try:
                idx = int(item_id)
            except ValueError:
                idx = self.tree.index(item_id)
            if 0 <= idx < len(self.labels):
                result.append(self.labels[idx])
        return result

    def _print_labels(self, labels: list[LabelData], job_name: str) -> None:
        if not labels:
            messagebox.showinfo("Baskı", "Basılacak etiket yok.")
            return
        printer = self.printer_var.get().strip()
        if not printer:
            messagebox.showerror("Yazıcı", "Yazıcı seçin.")
            return
        try:
            settings = self.settings_from_ui()
            payload = build_batch_tspl(labels, settings)
            send_raw(printer, payload, job_name=job_name)
        except Exception as exc:
            messagebox.showerror("Baskı hatası", str(exc))
            return
        self.persist_settings()
        self.status_var.set(f"{len(labels)} etiket gönderildi → {printer}")
        messagebox.showinfo("Baskı", f"{len(labels)} etiket yazıcıya gönderildi.")

    def print_test(self) -> None:
        """Geliştirici örnek şablonu basar (font Orta; marka: BYK PROJECT)."""
        printer = self.printer_var.get().strip()
        if not printer:
            messagebox.showerror("Yazıcı", "Yazıcı seçin.")
            return
        try:
            settings = self.settings_from_ui()
            # Uygulamadaki marka metnini kullanma — sabit örnek şablon
            settings.font_barkod = TEST_SAMPLE_FONT
            settings.font_ak = TEST_SAMPLE_FONT
            settings.font_item = TEST_SAMPLE_FONT
            settings.brand_text = TEST_SAMPLE_BRAND
            settings.brand_position = TEST_SAMPLE_BRAND_POS
            settings.copies = 1
            payload = build_batch_tspl([TEST_SAMPLE_LABEL], settings)
            send_raw(printer, payload, job_name="Biyik.dev Test Ornek")
        except Exception as exc:
            messagebox.showerror("Baskı hatası", str(exc))
            return
        self.status_var.set(f"Örnek test etiketi gönderildi → {printer}")
        messagebox.showinfo(
            "Test Baskı",
            "Örnek test etiketi yazıcıya gönderildi.\n\n"
            f"Barkod: {TEST_SAMPLE_LABEL.barkod}\n"
            f"A-K: {TEST_SAMPLE_LABEL.ak_barkod}\n"
            f"Marka: {TEST_SAMPLE_BRAND}\n"
            f"Font: Orta ({TEST_SAMPLE_FONT})",
        )

    def print_selected(self) -> None:
        self._print_labels(self._selected_labels(), "Barkod Selected")

    def print_all(self) -> None:
        visible = self._visible_labels()
        if not visible:
            messagebox.showinfo("Baskı", "Liste boş.")
            return
        filt = (self.filter_var.get() or "").strip()
        msg = f"{len(visible)} etiketin tamamı basılsın mı?"
        if filt:
            msg = (
                f"Filtre açık (“{filt}”).\n"
                f"Görünen {len(visible)} / {len(self.labels)} etiket basılsın mı?"
            )
        if not messagebox.askyesno("Onay", msg):
            return
        self._print_labels(visible, "Barkod Batch")


def main() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] in {"--print", "-p"}:
        cfg = load_config()
        path = sys.argv[2]
        cols = cfg.get("excel_columns", {})
        result = load_labels_from_excel(
            path,
            col_barkod=cols.get("barkod", "Barkod"),
            col_ak=cols.get("ak_barkod", "A-K Barkod"),
            col_item=cols.get("item_no", "ItemNo"),
            col_parca=cols.get("parca_ad", "ParcaAd"),
        )
        settings = settings_from_config(cfg)
        printer = cfg.get("printer_name") or default_printer()
        send_raw(printer, build_batch_tspl(result.labels, settings), "Barkod CLI")
        print(f"{len(result.labels)} etiket gönderildi → {printer}")
        return

    # Soft kurumsal açılış, ardından ana pencere
    if "--no-splash" not in sys.argv:
        show_splash()

    app = LabelApp()
    app.mainloop()


if __name__ == "__main__":
    main()
