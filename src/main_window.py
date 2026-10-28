r"""
BYK Seri Baskı Pro — Biyik.dev

Excel'deki ana barkod / 2. barkod / orta metin / alt metin satırlarını okuyup
TSPL ile termal etikete basar.

Çalıştırma (proje kökünden):
    python app.py
    Windows : scripts\windows\BASLAT.bat
    macOS   : scripts/macos/BASLAT.command

Paketleme:
    Windows : scripts\windows\BUILD_RELEASE.bat     →  Kurulum.exe zip
    macOS   : scripts/macos/BUILD_RELEASE_MAC.sh    →  .app zip
"""

from __future__ import annotations

import json
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from about_dialog import open_about
from app_icon import apply_app_icon
from branding import APP_DISPLAY, APP_TITLE, LABEL_CREDIT
from excel_loader import DEFAULT_HEADERS, ColumnHeaders, load_labels_from_excel, role_label
from help_dialog import open_help
from label_preview import render_label_photoimage
from label_entry_dialog import LabelEntryDialog
from layout_dialog import LayoutDialog
from paths import app_home, assets_dir, defaults_dir
from printer_compat import OK as PRINTER_OK
from printer_compat import WARN as PRINTER_WARN
from printer_compat import check_printer, pick_label_printer
from printer_raw import default_printer, list_printers, send_raw
from serial_dialog import open_serial_dialog
from splash import show_splash
from theme import STRIPE, apply_theme
from tspl_builder import (
    BARCODE_TYPES,
    BRAND_POSITIONS,
    BRAND_STYLES,
    FONT_SIZE_LABELS,
    LabelData,
    LabelSettings,
    build_batch_tspl,
    build_tspl,
    compute_layout,
    describe_layout,
    normalize_barcode_type,
)
from update_dialog import UpdateDialog
from updater import check_latest, current_version
from ui_icons import (
    C_GOLD,
    C_GREEN,
    C_MUTED,
    C_NAVY,
    C_TEAL,
    C_WARN,
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
        src = defaults_dir() / name
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


# Yerleşim ayarları (config anahtarı = LabelSettings alanı) → varsayılan
LAYOUT_DEFAULTS: dict[str, object] = {
    "show_main_text": True,
    "show_ak": True,
    "show_ak_text": True,
    "show_item": True,
    "show_parca": True,
    "ak_position": "below",
    "auto_fit": True,
    "max_text_lines": 2,
    "text_mode": "graphic",
    "offset_x_mm": 0.0,
    "offset_y_mm": 0.0,
}


def _brand_enabled(cfg: dict) -> bool:
    # Eski config: anahtar yoksa metin doluysa açık say
    return bool(cfg.get("brand_enabled", bool(cfg.get("brand_text"))))


def settings_from_config(cfg: dict, **overrides) -> LabelSettings:
    return LabelSettings(
        width_mm=float(overrides.get("width_mm", cfg.get("label_width_mm", 98))),
        height_mm=float(overrides.get("height_mm", cfg.get("label_height_mm", 98))),
        gap_mm=float(overrides.get("gap_mm", cfg.get("gap_mm", 3))),
        dpi=int(overrides.get("dpi", cfg.get("dpi", 203))),
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
        brand_enabled=bool(overrides.get("brand_enabled", _brand_enabled(cfg))),
        brand_style=str(overrides.get("brand_style", cfg.get("brand_style", "plain"))),
        barcode_narrow=int(overrides.get("barcode_narrow", cfg.get("barcode_narrow", 3))),
        gap_after_barcode_mm=float(
            overrides.get("gap_after_barcode_mm", cfg.get("gap_after_barcode_mm", 1.5))
        ),
        gap_after_text_mm=float(
            overrides.get(
                "gap_after_text_mm",
                cfg.get("gap_after_text_mm", cfg.get("gap_between_lines_mm", 2.5)),
            )
        ),
        gap_between_barcodes_mm=float(
            overrides.get(
                "gap_between_barcodes_mm", cfg.get("gap_between_barcodes_mm", 4)
            )
        ),
        margin_mm=float(overrides.get("margin_mm", cfg.get("margin_mm", 6))),
        **{
            key: type(default)(overrides.get(key, cfg.get(key, default)))
            for key, default in LAYOUT_DEFAULTS.items()
        },
    )


def _valid_dpi(raw: str) -> int:
    try:
        dpi = int(float(str(raw).strip() or 203))
    except ValueError:
        dpi = 0
    if not 100 <= dpi <= 1200:
        raise ValueError("DPI 100–1200 arası olmalı (genelde 203 veya 300).")
    return dpi


def _num(var: tk.Variable) -> float:
    return float(str(var.get()).replace(",", ".").strip() or 0)


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
        # Ekrana göre: liste ve önizlemeye yer kalsın (en fazla 1180x900)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{min(1180, sw - 40)}x{max(720, min(900, sh - 100))}")
        self.minsize(960, 720)
        apply_theme(self)

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
        self.dpi_var = tk.StringVar(value=str(self.cfg.get("dpi", 203)))
        self.printer_hint_var = tk.StringVar()
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
        self.brand_enabled_var = tk.BooleanVar(value=_brand_enabled(self.cfg))
        self.brand_style_var = tk.StringVar(
            value=str(self.cfg.get("brand_style", "plain"))
        )
        self.font_brand_var = tk.IntVar(value=int(self.cfg.get("font_brand", 1)))
        self.barcode_type_var = tk.StringVar(
            value=normalize_barcode_type(self.cfg.get("barcode_type", "128"))
        )
        self.ak_barcode_type_var = tk.StringVar(
            value=normalize_barcode_type(
                self.cfg.get("ak_barcode_type", self.cfg.get("barcode_type", "128"))
            )
        )
        self.status_var = tk.StringVar(value="Excel dosyasını yükleyin.")
        self._init_layout_vars()
        self._layout_dialog: LayoutDialog | None = None
        self._entry_dialog: LabelEntryDialog | None = None
        # Son çıkarma işlemi: (liste kimliği, çıkarma sonrası uzunluk, [(indeks, etiket)])
        self._undo: tuple[int, int, list[tuple[int, LabelData]]] | None = None
        self._update_info = None
        self._update_dialog: UpdateDialog | None = None
        self._update_result: tuple | None = None

        self._build_ui()
        self._load_printers()
        # İlk layout oturduktan sonra yükle — önizleme gerçek tuval boyutuna sığsın
        if Path(self.excel_path.get()).exists():
            self.after_idle(self.load_excel)
        if self.cfg.get("update_check", True):
            self.after(1500, lambda: self.check_updates(silent=True))

    def _init_layout_vars(self) -> None:
        """Yerleşim penceresinin bağlandığı değişkenler (config'ten)."""
        c = self.cfg

        def bvar(key: str) -> tk.BooleanVar:
            return tk.BooleanVar(value=bool(c.get(key, LAYOUT_DEFAULTS[key])))

        def svar(key: str, default) -> tk.StringVar:
            return tk.StringVar(value=str(c.get(key, default)))

        self.show_main_text_var = bvar("show_main_text")
        self.show_ak_var = bvar("show_ak")
        self.show_ak_text_var = bvar("show_ak_text")
        self.show_item_var = bvar("show_item")
        self.show_parca_var = bvar("show_parca")
        self.auto_fit_var = bvar("auto_fit")
        self.ak_pos_var = svar("ak_position", "below")
        self.text_mode_var = svar("text_mode", "graphic")
        self.max_lines_var = svar("max_text_lines", 2)
        self.offset_x_var = svar("offset_x_mm", 0)
        self.offset_y_var = svar("offset_y_mm", 0)
        self.margin_var = svar("margin_mm", 6)
        self.gap_after_bc_var = svar("gap_after_barcode_mm", 1.5)
        self.gap_barcodes_var = svar("gap_between_barcodes_mm", 4)
        self.gap_text_var = svar(
            "gap_after_text_mm", c.get("gap_between_lines_mm", 2.5)
        )
        self.narrow_var = svar("barcode_narrow", 3)
        for var in (
            self.show_main_text_var, self.show_ak_var, self.show_ak_text_var,
            self.show_item_var, self.show_parca_var, self.auto_fit_var,
            self.ak_pos_var, self.text_mode_var, self.max_lines_var,
            self.offset_x_var, self.offset_y_var, self.margin_var,
            self.gap_after_bc_var, self.gap_barcodes_var, self.gap_text_var,
            self.narrow_var,
        ):
            var.trace_add("write", lambda *_: self._refresh_preview())

    def _make_font_combo(self, parent, var: tk.IntVar, row: int, col: int) -> ttk.Combobox:
        combo = ttk.Combobox(
            parent,
            values=_font_combo_values(),
            state="readonly",
            width=12,
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
        pad = {"padx": 6, "pady": 2}

        # Soft kurumsal üst şerit
        header = tk.Frame(self, bg="#FFFFFF", highlightthickness=0)
        header.pack(side="top", fill="x")
        head_inner = tk.Frame(header, bg="#FFFFFF")
        head_inner.pack(fill="x", padx=14, pady=6)

        badge_path = assets_dir() / "biyik_badge.png"
        if badge_path.exists():
            try:
                from PIL import Image, ImageTk

                img = Image.open(badge_path).convert("RGBA").resize(
                    (36, 36), Image.Resampling.LANCZOS
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
        tk.Label(
            title_row,
            text=APP_DISPLAY,
            font=("Segoe UI Semibold", 15),
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

        head_tools = tk.Frame(head_inner, bg="#FFFFFF")
        head_tools.pack(side="right")
        for text, icon, cmd in (
            ("Kullanım", "book-open", self.show_help),
            ("Hakkında", "circle-info", self.show_about),
            ("Güncelleme", "cloud-arrow-down", lambda: self.check_updates(silent=False)),
        ):
            icon_button(head_tools, text, icon, cmd, self._icons, size=13, fill=C_NAVY).pack(
                side="left", padx=(6, 0)
            )

        self._header_sep = tk.Frame(self, bg="#E6E9EE", height=1)
        self._header_sep.pack(side="top", fill="x")
        self._build_update_banner()

        credit = ttk.Frame(self, style="Page.TFrame")
        credit.pack(side="bottom", fill="x", padx=12, pady=(2, 8))
        mail = ttk.Label(
            credit, text=CONTACT_EMAIL, style="Page.TLabel", foreground=C_NAVY, cursor="hand2"
        )
        mail.pack(side="right")
        ttk.Label(
            credit, text="BIYIK.DEV tarafından geliştirilmiştir  ·  ", style="Page.TLabel"
        ).pack(side="right")
        # width=1: uzun durum mesajı pencereyi genişletmez, sığdığı kadar görünür
        ttk.Label(
            credit, textvariable=self.status_var, style="Page.TLabel", foreground=C_NAVY,
            width=1,
        ).pack(side="left", fill="x", expand=True)
        mail.bind("<Button-1>", lambda _e: self._open_mail())

        actions = ttk.Frame(self, style="Page.TFrame")
        actions.pack(side="bottom", fill="x", padx=12, pady=(6, 2))
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
            fill="#FFFFFF",
            style="Primary.TButton",
        ).pack(side="left", padx=4)
        icon_button(
            actions,
            "Tümünü Bas",
            "layer-group",
            self.print_all,
            self._icons,
            fill="#FFFFFF",
            style="Primary.TButton",
        ).pack(side="left", padx=4)
        icon_button(
            actions,
            "Ayarları Kaydet",
            "floppy-disk",
            self.persist_settings,
            self._icons,
        ).pack(side="left", padx=4)

        top = icon_labelframe(
            self, "Kaynak / Yazıcı", "hard-drive", self._icons, fill=C_NAVY
        )
        top.pack(side="top", fill="x", padx=12, pady=(10, 4))

        excel_ic = self._icons.get("file-excel", size=13, fill=C_GREEN)
        excel_lbl = ttk.Frame(top)
        if excel_ic is not None:
            ttk.Label(excel_lbl, image=excel_ic).pack(side="left", padx=(0, 4))
        ttk.Label(excel_lbl, text="Excel:").pack(side="left")
        excel_lbl.grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(top, textvariable=self.excel_path, width=20).grid(
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
            top, textvariable=self.printer_var, width=20, state="readonly"
        )
        self.printer_combo.grid(row=1, column=1, sticky="ew", **pad)
        self.printer_combo.bind("<<ComboboxSelected>>", lambda _e: self._check_printer())
        icon_button(
            top, "Yenile", "arrows-rotate", self._load_printers, self._icons
        ).grid(row=1, column=2, **pad)
        self.printer_hint = ttk.Label(top, textvariable=self.printer_hint_var, wraplength=600)
        self.printer_hint.grid(row=2, column=1, columnspan=4, sticky="w", padx=6)
        # Not satırı kart genişliğine göre alt satıra geçer
        top.bind(
            "<Configure>",
            lambda e: self.printer_hint.configure(wraplength=max(300, e.width - 140)),
        )
        top.columnconfigure(1, weight=1)

        # Ayarlar tek kartta iki sekme: dikey alan liste ve önizlemeye kalır
        settings_card = icon_labelframe(
            self, "Etiket ve baskı ayarları", "sliders", self._icons, fill=C_NAVY
        )
        settings_card.pack(side="top", fill="x", padx=12, pady=4)
        settings_tabs = ttk.Notebook(settings_card)
        settings_tabs.pack(fill="x")
        settings = ttk.Frame(settings_tabs, padding=(4, 6, 4, 2))
        duo = ttk.Frame(settings_tabs, padding=(4, 6, 4, 2))
        for frame, text, icon in (
            (settings, "Etiket ve barkod", "barcode"),
            (duo, "Fontlar ve markalama", "stamp"),
        ):
            ic = self._icons.get(icon, size=12, fill=C_NAVY)
            if ic is not None:
                settings_tabs.add(frame, text=f" {text}", image=ic, compound="left")
            else:
                settings_tabs.add(frame, text=text)

        # 4 sütunlu ızgara: etiket + alan çiftleri (pencereye sığar)
        def field(label: str, var: tk.StringVar, row: int, col: int) -> ttk.Label:
            lbl = ttk.Label(settings, text=label)
            lbl.grid(row=row, column=col * 2, sticky="e", **pad)
            ttk.Entry(settings, textvariable=var, width=6).grid(
                row=row, column=col * 2 + 1, sticky="w", **pad
            )
            var.trace_add("write", lambda *_: self._refresh_preview())
            return lbl

        field("Genişlik", self.width_var, 0, 0)
        field("Yükseklik", self.height_var, 0, 1)
        field("Gap", self.gap_var, 0, 2)
        # DPI: yazıcının çözünürlüğü (etiket altında / kutusunda yazar)
        ttk.Label(settings, text="DPI").grid(row=0, column=6, sticky="e", **pad)
        ttk.Combobox(
            settings, textvariable=self.dpi_var, values=("203", "300", "600"), width=6
        ).grid(row=0, column=7, sticky="w", **pad)
        self.dpi_var.trace_add("write", lambda *_: self._refresh_preview())

        field("Kopya", self.copies_var, 1, 0)
        field("Yoğunluk", self.density_var, 1, 1)
        field("Barkod yük.", self.bc_height_var, 1, 2)
        self.lbl_ak_height = field("2. barkod yük.", self.ak_bc_height_var, 1, 3)

        type_values = [f"{k} — {v}" for k, v in BARCODE_TYPES.items()]
        ttk.Label(settings, text="Ana barkod tipi").grid(row=2, column=0, sticky="e", **pad)
        self.bc_type_combo = ttk.Combobox(
            settings, values=type_values, state="readonly", width=16
        )
        cur_bc = self.barcode_type_var.get()
        self.bc_type_combo.set(f"{cur_bc} — {BARCODE_TYPES.get(cur_bc, cur_bc)}")
        self.bc_type_combo.grid(row=2, column=1, columnspan=3, sticky="w", **pad)
        self.bc_type_combo.bind("<<ComboboxSelected>>", self._on_bc_type_change)

        ttk.Label(settings, text="2. barkod tipi").grid(row=2, column=4, sticky="e", **pad)
        self.ak_type_combo = ttk.Combobox(
            settings, values=type_values, state="readonly", width=16
        )
        cur_ak = self.ak_barcode_type_var.get()
        self.ak_type_combo.set(f"{cur_ak} — {BARCODE_TYPES.get(cur_ak, cur_ak)}")
        self.ak_type_combo.grid(row=2, column=5, columnspan=3, sticky="w", **pad)
        self.ak_type_combo.bind("<<ComboboxSelected>>", self._on_ak_type_change)

        ttk.Label(
            settings,
            text="Ölçüler mm cinsindendir. QR seçiliyse yükseklik, kare kenarı olarak kullanılır.",
            style="Muted.TLabel",
        ).grid(row=3, column=0, columnspan=8, sticky="w", padx=6, pady=(0, 2))

        # Fontlar + Markalama yan yana (ikinci sekme)
        duo.columnconfigure(0, weight=0)
        duo.columnconfigure(2, weight=1)

        # İç içe kart yerine sade bölüm başlıkları (sekme alçak kalır)
        fonts = ttk.Frame(duo)
        fonts.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        brand = ttk.Frame(duo)
        brand.grid(row=0, column=2, sticky="nsew", padx=(12, 0))
        ttk.Separator(duo, orient="vertical").grid(row=0, column=1, sticky="ns")
        ttk.Label(fonts, text="Baskı fontları", style="Section.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 2)
        )
        ttk.Label(brand, text="Markalama", style="Section.TLabel").grid(
            row=0, column=0, columnspan=4, sticky="w", padx=6, pady=(0, 2)
        )

        self.lbl_font_barkod = ttk.Label(fonts, text="Ana barkod metni:")
        self.lbl_font_barkod.grid(row=1, column=0, sticky="e", **pad)
        self._make_font_combo(fonts, self.font_barkod_var, 1, 1)

        self.lbl_font_ak = ttk.Label(fonts, text="2. barkod metni:")
        self.lbl_font_ak.grid(row=2, column=0, sticky="e", **pad)
        self._make_font_combo(fonts, self.font_ak_var, 2, 1)

        self.lbl_font_item = ttk.Label(fonts, text="Orta / alt metin:")
        self.lbl_font_item.grid(row=3, column=0, sticky="e", **pad)
        self._make_font_combo(fonts, self.font_item_var, 3, 1)

        brand.columnconfigure(1, weight=1)

        ttk.Checkbutton(
            brand,
            text="Marka bas",
            variable=self.brand_enabled_var,
            command=self._on_brand_toggle,
        ).grid(row=1, column=0, sticky="w", **pad)
        self.brand_entry = ttk.Entry(brand, textvariable=self.brand_text_var)
        self.brand_entry.grid(row=1, column=1, columnspan=3, sticky="ew", **pad)
        self.brand_text_var.trace_add("write", lambda *_: self._refresh_preview())

        ttk.Label(brand, text="Konum").grid(row=2, column=0, sticky="e", **pad)
        pos_values = [f"{k} — {v}" for k, v in BRAND_POSITIONS.items()]
        self.brand_pos_combo = ttk.Combobox(
            brand, values=pos_values, state="readonly", width=11
        )
        cur_pos = self.brand_pos_var.get()
        self.brand_pos_combo.set(
            f"{cur_pos} — {BRAND_POSITIONS.get(cur_pos, 'Alt')}"
        )
        self.brand_pos_combo.grid(row=2, column=1, sticky="w", **pad)
        self.brand_pos_combo.bind("<<ComboboxSelected>>", self._on_brand_pos_change)

        ttk.Label(brand, text="Boyut").grid(row=2, column=2, sticky="e", **pad)
        self.brand_font_combo = self._make_font_combo(brand, self.font_brand_var, 2, 3)

        ttk.Label(brand, text="Stil").grid(row=3, column=0, sticky="e", **pad)
        self.brand_style_combo = ttk.Combobox(
            brand,
            values=[f"{k} — {v}" for k, v in BRAND_STYLES.items()],
            state="readonly",
            width=20,
        )
        cur_style = self.brand_style_var.get()
        self.brand_style_combo.set(
            f"{cur_style} — {BRAND_STYLES.get(cur_style, BRAND_STYLES['plain'])}"
        )
        self.brand_style_combo.grid(row=3, column=1, columnspan=3, sticky="w", **pad)
        self.brand_style_combo.bind("<<ComboboxSelected>>", self._on_brand_style_change)

        ttk.Label(
            brand,
            text=f"Etiketin üstünde her zaman: “{LABEL_CREDIT}”",
            style="Muted.TLabel",
        ).grid(row=4, column=0, columnspan=4, sticky="w", padx=6, pady=(0, 2))
        self._on_brand_toggle()

        body = ttk.Frame(self, style="Page.TFrame")
        body.pack(side="top", fill="both", expand=True, padx=12, pady=(4, 4))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=0, minsize=260)
        body.rowconfigure(0, weight=1)

        self.list_frame = icon_labelframe(
            body,
            "Etiket listesi",
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

        # Elle düzenleme: Excel'i açmadan seri ekle / çıkar
        edit_bar = ttk.Frame(self.list_frame)
        edit_bar.pack(fill="x", padx=8, pady=(6, 0))
        icon_button(
            edit_bar, "Seri ekle…", "circle-plus", self.open_add_label, self._icons,
            size=12, fill=C_GREEN,
        ).pack(side="left")
        icon_button(
            edit_bar, "Seçilileri çıkar", "circle-minus", self.remove_selected,
            self._icons, size=12, fill="#D93025",
        ).pack(side="left", padx=4)
        self.btn_undo = icon_button(
            edit_bar, "Geri al", "rotate-left", self.undo_remove, self._icons,
            size=12, fill=C_NAVY,
        )
        self.btn_undo.pack(side="left")
        self.btn_undo.state(["disabled"])
        self.count_var = tk.StringVar(value="0 etiket")
        ttk.Label(edit_bar, textvariable=self.count_var, style="Muted.TLabel").pack(
            side="right"
        )

        cols = ("barkod", "ak", "item", "parca")
        tree_wrap = ttk.Frame(self.list_frame)
        tree_wrap.pack(side="top", fill="both", expand=True, padx=8, pady=8)
        self.tree = ttk.Treeview(
            tree_wrap, columns=cols, show="headings", selectmode="extended", height=4
        )
        self.tree.heading("barkod", text=DEFAULT_HEADERS["barkod"])
        self.tree.heading("ak", text=DEFAULT_HEADERS["ak_barkod"])
        self.tree.heading("item", text=DEFAULT_HEADERS["item_no"])
        self.tree.heading("parca", text=DEFAULT_HEADERS["parca_ad"])
        self.tree.column("barkod", width=160)
        self.tree.column("ak", width=120)
        self.tree.column("item", width=120)
        self.tree.column("parca", width=160)
        scroll = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.tree.tag_configure("odd", background=STRIPE)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Delete>", lambda _e: self.remove_selected())
        self.tree.bind("<BackSpace>", lambda _e: self.remove_selected())
        self.bind("<Control-z>", self._on_undo_key)
        self.bind("<Command-z>", self._on_undo_key)

        self.tree_menu = tk.Menu(self, tearoff=0)
        self.tree_menu.add_command(label="Seri ekle…", command=self.open_add_label)
        self.tree_menu.add_command(
            label="Seçilileri listeden çıkar", command=self.remove_selected
        )
        self.tree_menu.add_separator()
        self.tree_menu.add_command(label="Geri al", command=self.undo_remove)
        for seq in ("<Button-3>", "<Button-2>", "<Control-Button-1>"):
            self.tree.bind(seq, self._show_tree_menu)

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

        preview_bar = ttk.Frame(tab_visual)
        preview_bar.pack(side="bottom", fill="x", padx=6, pady=(0, 6))
        icon_button(
            preview_bar,
            "Yerleşim ayarları…",
            "sliders",
            self.open_layout,
            self._icons,
            size=12,
            fill=C_TEAL,
        ).pack(side="top", fill="x")
        self.fit_note_var = tk.StringVar()
        self.fit_note_lbl = ttk.Label(
            preview_bar, textvariable=self.fit_note_var, wraplength=250, justify="left"
        )
        self.fit_note_lbl.pack(side="top", fill="x", pady=(4, 0))

        # Başlangıç boyutu yalnızca ilk layout için; sonra alanla ölçeklenir
        self.preview_canvas = tk.Canvas(
            tab_visual, width=260, height=120, bg="#F0F0F0", highlightthickness=0
        )
        self.preview_canvas.pack(fill="both", expand=True, padx=6, pady=6)
        self.preview_canvas.bind("<Configure>", self._on_preview_configure)
        self.preview_canvas.bind("<Double-Button-1>", lambda _e: self.open_layout())

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

    def _on_brand_toggle(self) -> None:
        """Marka kapalıyken metin ve tasarım alanları pasif."""
        on = bool(self.brand_enabled_var.get())
        self.brand_entry.configure(state="normal" if on else "disabled")
        for combo in (self.brand_pos_combo, self.brand_font_combo, self.brand_style_combo):
            combo.configure(state="readonly" if on else "disabled")
        self._refresh_preview()

    def _on_brand_style_change(self, _event=None) -> None:
        raw = (self.brand_style_combo.get() or "plain").split("—", 1)[0].strip()
        self.brand_style_var.set(raw if raw in BRAND_STYLES else "plain")
        self._refresh_preview()

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
            # Önce etiket yazıcısı gibi görünen; yoksa sistem varsayılanı
            choice = pick_label_printer(printers)
            if not choice:
                try:
                    d = default_printer()
                    choice = d if d in printers else printers[0]
                except Exception:
                    choice = printers[0]
            self.printer_var.set(choice)
        self._check_printer()

    def _check_printer(self) -> None:
        """Seçili yazıcının TSPL uyumluluğunu göster."""
        result = check_printer(self.printer_var.get())
        color = {PRINTER_OK: C_GREEN, PRINTER_WARN: "#D93025"}.get(result.status, C_WARN)
        mark = {PRINTER_OK: "✓", PRINTER_WARN: "⚠"}.get(result.status, "?")
        self.printer_hint_var.set(f"{mark} {result.message}")
        self.printer_hint.configure(foreground=color)

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
        """
        Liste başlıkları Excel 1. satırını gösterir (kullanıcının kendi verisi);
        ayar etiketleri evrensel rol adlarıdır: "2. barkod (M Barkod)" gibi.
        """
        self.column_headers = headers
        h = headers

        self.tree.heading("barkod", text=h.barkod)
        self.tree.heading("ak", text=h.ak_barkod)
        self.tree.heading("item", text=h.item_no)
        self.tree.heading("parca", text=h.parca_ad)

        self.lbl_font_barkod.configure(text=f"{role_label('barkod', h)} metni:")
        self.lbl_font_ak.configure(text=f"{role_label('ak_barkod', h)} metni:")
        self.lbl_font_item.configure(text="Orta / alt metin:")
        self.lbl_ak_height.configure(text="2. barkod yük.")

    def load_excel(self) -> None:
        path = Path(self.excel_path.get())
        cols = self.cfg.get("excel_columns", {})
        try:
            result = load_labels_from_excel(
                path,
                col_barkod=cols.get("barkod", "Barkod"),
                col_ak=cols.get("ak_barkod", ""),
                col_item=cols.get("item_no", ""),
                col_parca=cols.get("parca_ad", ""),
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
            stripe = ("odd",) if len(self.tree.get_children()) % 2 else ()
            self.tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(lab.barkod, lab.ak_barkod, lab.item_no, lab.parca_ad),
                tags=stripe,
            )

        shown = len(self.tree.get_children())
        total = len(self.labels)
        self.count_var.set(f"{shown} / {total} etiket" if query else f"{total} etiket")
        if query:
            self.status_var.set(f"Filtre: “{query}”  ·  {shown} / {total} satır")
        self._update_undo_button()

    # ── Elle seri ekle / çıkar ───────────────────────────────────────

    def _show_tree_menu(self, event: tk.Event) -> None:
        row = self.tree.identify_row(event.y)
        if row and row not in self.tree.selection():
            self.tree.selection_set(row)
        self.tree_menu.tk_popup(event.x_root, event.y_root)

    def open_add_label(self) -> None:
        if self._entry_dialog is not None and self._entry_dialog.winfo_exists():
            self._entry_dialog.lift()
            return
        self._entry_dialog = LabelEntryDialog(
            self,
            self.column_headers,
            on_add=self._add_label,
            exists=lambda code: any(lab.barkod == code for lab in self.labels),
        )

    def _add_label(self, label: LabelData) -> bool:
        self.labels.append(label)
        if self.filter_var.get():
            self.filter_var.set("")  # yeni satır görünsün
        else:
            self._rebuild_tree()
        iid = str(len(self.labels) - 1)
        self.tree.selection_set(iid)
        self.tree.focus(iid)
        self.tree.see(iid)
        self._show_preview(label)
        self.status_var.set(f"Listeye eklendi: {label.barkod}")
        return True

    def remove_selected(self) -> None:
        """Seçili satırları listeden çıkarır (Excel dosyası değişmez)."""
        indices = sorted(
            {int(i) for i in self.tree.selection() if str(i).isdigit()}
        )
        indices = [i for i in indices if 0 <= i < len(self.labels)]
        if not indices:
            self.status_var.set("Çıkarmak için listeden satır seçin.")
            return
        visible = list(self.tree.get_children())
        pos = visible.index(str(indices[0])) if str(indices[0]) in visible else 0

        removed = [(i, self.labels[i]) for i in indices]
        for i in reversed(indices):
            del self.labels[i]
        self._undo = (id(self.labels), len(self.labels), removed)
        self._rebuild_tree()

        rows = self.tree.get_children()
        if rows:
            nxt = rows[min(pos, len(rows) - 1)]
            self.tree.selection_set(nxt)
            self.tree.focus(nxt)
            self.tree.see(nxt)
            self._show_preview(self.labels[int(nxt)])
        else:
            self._current_label = None
            self.preview_canvas.delete("all")
            self.preview_text.delete("1.0", "end")
        names = ", ".join(lab.barkod for _, lab in removed[:3])
        more = f" +{len(removed) - 3}" if len(removed) > 3 else ""
        self.status_var.set(
            f"{len(removed)} seri listeden çıkarıldı ({names}{more})  ·  Geri al: Ctrl/⌘+Z"
        )

    def _on_undo_key(self, event: tk.Event) -> None:
        # Yazı alanındayken Ctrl+Z listeyi değiştirmesin
        if isinstance(event.widget, (tk.Entry, ttk.Entry, tk.Text, ttk.Combobox)):
            return
        self.undo_remove()

    def _undo_valid(self) -> bool:
        return (
            self._undo is not None
            and self._undo[0] == id(self.labels)
            and self._undo[1] == len(self.labels)
        )

    def _update_undo_button(self) -> None:
        if hasattr(self, "btn_undo"):
            self.btn_undo.state(["!disabled"] if self._undo_valid() else ["disabled"])

    def undo_remove(self) -> None:
        if not self._undo_valid():
            self._undo = None
            self._update_undo_button()
            return
        assert self._undo is not None
        removed = self._undo[2]
        self._undo = None
        for i, lab in removed:  # artan sırayla → eski yerlerine
            self.labels.insert(i, lab)
        if self.filter_var.get():
            self.filter_var.set("")
        else:
            self._rebuild_tree()
        iids = [str(i) for i, _ in removed]
        self.tree.selection_set(iids)
        self.tree.see(iids[0])
        self._show_preview(removed[0][1])
        self.status_var.set(f"{len(removed)} seri geri alındı.")

    def settings_from_ui(self) -> LabelSettings:
        try:
            return settings_from_config(
                self.cfg,
                width_mm=float(self.width_var.get().replace(",", ".")),
                height_mm=float(self.height_var.get().replace(",", ".")),
                gap_mm=float(self.gap_var.get().replace(",", ".")),
                copies=max(1, int(self.copies_var.get())),
                density=int(self.density_var.get()),
                dpi=_valid_dpi(self.dpi_var.get()),
                barcode_height_mm=float(self.bc_height_var.get().replace(",", ".")),
                ak_barcode_height_mm=float(
                    self.ak_bc_height_var.get().replace(",", ".")
                ),
                font_barkod=int(self.font_barkod_var.get()),
                font_ak=int(self.font_ak_var.get()),
                font_item=int(self.font_item_var.get()),
                brand_text=self.brand_text_var.get().strip(),
                brand_position=self.brand_pos_var.get().strip() or "bottom",
                brand_enabled=bool(self.brand_enabled_var.get()),
                brand_style=self.brand_style_var.get() or "plain",
                barcode_type=normalize_barcode_type(self.barcode_type_var.get()),
                ak_barcode_type=normalize_barcode_type(self.ak_barcode_type_var.get()),
                font_brand=int(self.font_brand_var.get()),
                barcode_narrow=max(1, min(6, int(_num(self.narrow_var)))),
                margin_mm=max(0.0, _num(self.margin_var)),
                gap_after_barcode_mm=max(0.0, _num(self.gap_after_bc_var)),
                gap_between_barcodes_mm=max(0.0, _num(self.gap_barcodes_var)),
                gap_after_text_mm=max(0.0, _num(self.gap_text_var)),
                offset_x_mm=_num(self.offset_x_var),
                offset_y_mm=_num(self.offset_y_var),
                max_text_lines=max(1, min(4, int(_num(self.max_lines_var)))),
                show_main_text=bool(self.show_main_text_var.get()),
                show_ak=bool(self.show_ak_var.get()),
                show_ak_text=bool(self.show_ak_text_var.get()),
                show_item=bool(self.show_item_var.get()),
                show_parca=bool(self.show_parca_var.get()),
                auto_fit=bool(self.auto_fit_var.get()),
                ak_position=self.ak_pos_var.get() or "below",
                text_mode=self.text_mode_var.get() or "graphic",
            )
        except (ValueError, tk.TclError) as exc:
            if "DPI" in str(exc):
                raise
            raise ValueError("Boyut / font / kopya / DPI alanları sayı olmalı.") from exc

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
                "dpi": s.dpi,
                "barcode_height_mm": s.barcode_height_mm,
                "ak_barcode_height_mm": s.ak_barcode_height_mm,
                "font_barkod": s.font_barkod,
                "font_ak": s.font_ak,
                "font_item": s.font_item,
                "font_brand": s.font_brand,
                "brand_text": s.brand_text,
                "brand_position": s.brand_position,
                "brand_enabled": s.brand_enabled,
                "brand_style": s.brand_style,
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
                **{key: getattr(s, key) for key in LAYOUT_DEFAULTS},
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
        if self._layout_dialog is not None:
            self._layout_dialog.refresh()

    def preview_label(self) -> LabelData:
        """Yerleşim penceresinde gösterilecek etiket (seçili yoksa örnek)."""
        return self._current_label or TEST_SAMPLE_LABEL

    def open_layout(self) -> None:
        if self._layout_dialog is not None and self._layout_dialog.winfo_exists():
            self._layout_dialog.lift()
            self._layout_dialog.focus_force()
            return
        self._layout_dialog = LayoutDialog(self)

    def _show_preview(self, label: LabelData) -> None:
        self._current_label = label
        try:
            settings = self.settings_from_ui()
        except ValueError:
            return

        cw, ch = self._preview_canvas_size()

        self.preview_canvas.delete("all")
        try:
            photo, _ = render_label_photoimage(
                label, settings, max_size=(max(64, cw - 12), max(64, ch - 12))
            )
            self._preview_photo = photo
            self.preview_canvas.create_image(cw // 2, ch // 2, image=photo)
            layout = compute_layout(label, settings)
            self.fit_note_var.set(layout.fit_note)
            self.fit_note_lbl.configure(
                foreground="#D93025" if layout.overflow else C_WARN
            )
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
        if not self._confirm_printer(printer):
            return
        try:
            settings = self.settings_from_ui()
        except ValueError as exc:
            messagebox.showerror("Ayar", str(exc))
            return
        bad = next(
            (lab for lab in labels[:200] if compute_layout(lab, settings).overflow),
            None,
        )
        if bad is not None and not messagebox.askyesno(
            "Etikete sığmıyor",
            f"En az bir etiket ({bad.barkod}) kağıda sığmıyor; bazı alanlar "
            "kesilebilir.\n\n“Yerleşim ayarları” ile düzeltebilirsiniz.\n"
            "Yine de basılsın mı?",
        ):
            return
        try:
            payload = build_batch_tspl(labels, settings)
            send_raw(printer, payload, job_name=job_name)
        except Exception as exc:
            messagebox.showerror("Baskı hatası", str(exc))
            return
        self.persist_settings()
        self.status_var.set(f"{len(labels)} etiket gönderildi → {printer}")
        messagebox.showinfo("Baskı", f"{len(labels)} etiket yazıcıya gönderildi.")

    def _confirm_printer(self, printer: str) -> bool:
        result = check_printer(printer)
        if result.status != PRINTER_WARN:
            return True
        return messagebox.askyesno(
            "Yazıcı uyumluluğu",
            f"“{printer}”\n\n{result.message}\n\nYine de gönderilsin mi?",
            parent=self,
        )

    def print_test(self) -> None:
        """Geliştirici örnek şablonu basar (font Orta; marka: BYK PROJECT)."""
        printer = self.printer_var.get().strip()
        if not printer:
            messagebox.showerror("Yazıcı", "Yazıcı seçin.")
            return
        if not self._confirm_printer(printer):
            return
        try:
            settings = self.settings_from_ui()
            # Uygulamadaki marka metnini kullanma — sabit örnek şablon
            settings.font_barkod = TEST_SAMPLE_FONT
            settings.font_ak = TEST_SAMPLE_FONT
            settings.font_item = TEST_SAMPLE_FONT
            settings.brand_text = TEST_SAMPLE_BRAND
            settings.brand_enabled = True
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
            f"2. barkod: {TEST_SAMPLE_LABEL.ak_barkod}\n"
            f"Marka: {TEST_SAMPLE_BRAND}\n"
            f"Font: Orta ({TEST_SAMPLE_FONT})",
        )

    # ── Güncelleme ───────────────────────────────────────────────────

    def _build_update_banner(self) -> None:
        bg = "#FFF4D6"
        self._update_banner = tk.Frame(self, bg=bg)
        inner = tk.Frame(self._update_banner, bg=bg)
        inner.pack(fill="x", padx=14, pady=6)
        ic = self._icons.get("cloud-arrow-down", size=14, fill=C_WARN)
        if ic is not None:
            tk.Label(inner, image=ic, bg=bg).pack(side="left", padx=(0, 6))
        self._update_text = tk.StringVar()
        tk.Label(
            inner,
            textvariable=self._update_text,
            bg=bg,
            fg="#5C4A12",
            font=("Segoe UI Semibold", 10),
        ).pack(side="left")
        ttk.Button(inner, text="Kapat", command=self._update_banner.pack_forget).pack(
            side="right"
        )
        ttk.Button(inner, text="Güncelle…", command=self._show_update_dialog).pack(
            side="right", padx=6
        )

    def check_updates(self, silent: bool) -> None:
        """GitHub'da yeni sürüm var mı? Ağ işi arka planda; sonuç ana döngüde."""
        if self._update_result == "pending":
            return
        self._update_result = "pending"
        if not silent:
            self.status_var.set("Güncellemeler denetleniyor…")

        def work() -> None:
            try:
                self._update_result = ("ok", check_latest())
            except Exception as exc:
                self._update_result = ("err", exc)

        threading.Thread(target=work, daemon=True).start()
        self.after(300, lambda: self._poll_update(silent))

    def _poll_update(self, silent: bool) -> None:
        result = self._update_result
        if result == "pending":
            self.after(300, lambda: self._poll_update(silent))
            return
        self._update_result = None
        kind, value = result  # type: ignore[misc]
        if kind == "err":
            if not silent:
                self.status_var.set("")
                messagebox.showwarning(
                    "Güncelleme",
                    f"Güncelleme sunucusuna ulaşılamadı.\n{value}",
                    parent=self,
                )
            return
        info = value
        if info is None:
            if not silent:
                self.status_var.set("")
                messagebox.showinfo(
                    "Güncelleme",
                    f"En güncel sürümü kullanıyorsunuz (v{current_version()}).",
                    parent=self,
                )
            return
        self._update_info = info
        self._update_text.set(
            f"Güncelleme geldi: v{info.version} hazır  "
            f"(kullandığınız: v{current_version()})"
        )
        self._update_banner.pack(side="top", fill="x", after=self._header_sep)
        if not silent or self.cfg.get("update_skip_version") != info.version:
            self._show_update_dialog()

    def _show_update_dialog(self) -> None:
        if self._update_info is None:
            return
        if self._update_dialog is not None and self._update_dialog.winfo_exists():
            self._update_dialog.lift()
            return
        self._update_dialog = UpdateDialog(
            self,
            self._update_info,
            on_skip=self._skip_update,
            on_ready_to_quit=self._quit_for_update,
        )

    def _skip_update(self, version: str) -> None:
        self.cfg["update_skip_version"] = version
        save_config(self.cfg)
        self._update_banner.pack_forget()

    def _quit_for_update(self) -> None:
        """Güncelleyici bu sürecin kapanmasını bekliyor."""
        try:
            self.persist_settings()
        except Exception:
            pass
        self.destroy()

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
            col_ak=cols.get("ak_barkod", ""),
            col_item=cols.get("item_no", ""),
            col_parca=cols.get("parca_ad", ""),
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
