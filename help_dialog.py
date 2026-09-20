"""Kullanım kılavuzu — güncel özellikler, ipuçları ve premium yol haritası."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageTk

from app_icon import apply_app_icon
from paths import assets_dir
from ui_icons import C_MUTED as ICON_MUTED
from ui_icons import IconStore, icon_button, titled_label

ASSETS = assets_dir()

C_BG = "#F3F5F7"
C_CARD = "#FFFFFF"
C_LINE = "#E6E9EE"
C_TEXT = "#2A3340"
C_MUTED = "#6B7380"
C_NAVY = "#1B3352"
C_ACCENT = "#B8962E"
C_CHIP = "#F0F3F7"
C_STEP = "#E8EEF5"


def _load_photo(path: Path, size: int, store: list) -> ImageTk.PhotoImage | None:
    if not path.exists():
        return None
    img = Image.open(path).convert("RGBA")
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    photo = ImageTk.PhotoImage(img)
    store.append(photo)
    return photo


def _section(parent: tk.Frame, title: str, icons: IconStore, icon: str) -> tk.Frame:
    box = tk.Frame(parent, bg=C_CARD, highlightbackground=C_LINE, highlightthickness=1)
    box.pack(fill="x", pady=(0, 12))
    inner = tk.Frame(box, bg=C_CARD)
    inner.pack(fill="x", padx=14, pady=12)
    titled_label(
        inner,
        title,
        icon,
        icons,
        size=14,
        fill=C_NAVY,
        font=("Segoe UI Semibold", 11),
        bg=C_CARD,
        fg=C_NAVY,
    ).pack(fill="x")
    tk.Frame(inner, bg=C_ACCENT, height=2).pack(anchor="w", pady=(4, 10), ipadx=22)
    return inner


def _p(parent: tk.Frame, text: str, *, muted: bool = False, bold: bool = False) -> None:
    tk.Label(
        parent,
        text=text,
        font=("Segoe UI Semibold", 9) if bold else ("Segoe UI", 9),
        fg=C_MUTED if muted else C_TEXT,
        bg=parent.cget("bg") if parent.cget("bg") else C_CARD,
        wraplength=520,
        justify="left",
        anchor="w",
    ).pack(fill="x", pady=(0, 6))


def _bullet(parent: tk.Frame, text: str) -> None:
    bg = parent.cget("bg") or C_CARD
    row = tk.Frame(parent, bg=bg)
    row.pack(fill="x", pady=1)
    tk.Label(row, text="•", font=("Segoe UI", 9), fg=C_ACCENT, bg=bg, width=2).pack(
        side="left", anchor="n"
    )
    tk.Label(
        row,
        text=text,
        font=("Segoe UI", 9),
        fg=C_TEXT,
        bg=bg,
        wraplength=500,
        justify="left",
        anchor="w",
    ).pack(side="left", fill="x", expand=True)


def _chip_row(parent: tk.Frame, items: list[str]) -> None:
    wrap = tk.Frame(parent, bg=C_CARD)
    wrap.pack(fill="x", pady=(2, 8))
    for text in items:
        chip = tk.Frame(wrap, bg=C_CHIP, highlightbackground=C_LINE, highlightthickness=1)
        chip.pack(side="left", padx=(0, 6), pady=3)
        tk.Label(
            chip,
            text=text,
            font=("Segoe UI", 8),
            fg=C_NAVY,
            bg=C_CHIP,
            padx=8,
            pady=3,
        ).pack()


def _step(parent: tk.Frame, num: str, title: str, detail: str) -> None:
    row = tk.Frame(parent, bg=C_STEP)
    row.pack(fill="x", pady=4)
    inner = tk.Frame(row, bg=C_STEP)
    inner.pack(fill="x", padx=10, pady=8)
    head = tk.Frame(inner, bg=C_STEP)
    head.pack(fill="x")
    tk.Label(
        head,
        text=num,
        font=("Segoe UI Semibold", 10),
        fg=C_ACCENT,
        bg=C_STEP,
        width=3,
        anchor="w",
    ).pack(side="left")
    tk.Label(
        head,
        text=title,
        font=("Segoe UI Semibold", 9),
        fg=C_NAVY,
        bg=C_STEP,
        anchor="w",
    ).pack(side="left")
    tk.Label(
        inner,
        text=detail,
        font=("Segoe UI", 9),
        fg=C_TEXT,
        bg=C_STEP,
        wraplength=500,
        justify="left",
        anchor="w",
    ).pack(fill="x", pady=(4, 0))


def open_help(parent: tk.Tk | tk.Toplevel, app_title: str) -> None:
    """Güncel Kullanım kılavuzu."""
    win = tk.Toplevel(parent)
    win.title("Kullanım Kılavuzu")
    apply_app_icon(win)
    win.configure(bg=C_BG)
    win.resizable(True, True)
    win.minsize(600, 540)
    win.transient(parent)
    win.grab_set()

    width, height = 640, 720
    win.geometry(f"{width}x{height}")
    win.update_idletasks()
    px = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
    py = parent.winfo_rooty() + max(0, (parent.winfo_height() - height) // 2)
    win.geometry(f"+{max(0, px)}+{max(0, py)}")

    photos: list[ImageTk.PhotoImage] = []
    icons = IconStore()

    header = tk.Frame(win, bg=C_CARD)
    header.pack(fill="x")
    head_inner = tk.Frame(header, bg=C_CARD)
    head_inner.pack(fill="x", padx=22, pady=16)

    badge = _load_photo(ASSETS / "biyik_badge.png", 52, photos)
    if badge:
        tk.Label(head_inner, image=badge, bg=C_CARD).pack(side="left", padx=(0, 12))

    titles = tk.Frame(head_inner, bg=C_CARD)
    titles.pack(side="left")
    titled_label(
        titles,
        "Kullanım Kılavuzu",
        "book-open",
        icons,
        size=18,
        fill=C_ACCENT,
        font=("Segoe UI Semibold", 15),
        bg=C_CARD,
        fg=C_NAVY,
    ).pack(anchor="w")
    tk.Label(
        titles,
        text=app_title,
        font=("Segoe UI", 9),
        fg=C_MUTED,
        bg=C_CARD,
        anchor="w",
    ).pack(anchor="w", pady=(2, 0))
    tk.Label(
        titles,
        text="Excel → önizleme → TSPL etiket baskısı  ·  BIYIK.DEV",
        font=("Segoe UI", 8),
        fg=C_ACCENT,
        bg=C_CARD,
        anchor="w",
    ).pack(anchor="w", pady=(4, 0))

    tk.Frame(header, bg=C_LINE, height=1).pack(fill="x")

    shell = tk.Frame(win, bg=C_BG)
    shell.pack(fill="both", expand=True)

    canvas = tk.Canvas(shell, bg=C_BG, highlightthickness=0)
    scroll = ttk.Scrollbar(shell, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    content = tk.Frame(canvas, bg=C_BG)
    win_id = canvas.create_window((0, 0), window=content, anchor="nw")

    def _on_configure(_e=None) -> None:
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfigure(win_id, width=canvas.winfo_width())

    content.bind("<Configure>", _on_configure)
    canvas.bind("<Configure>", _on_configure)

    def _on_mousewheel(event) -> None:
        # Windows / macOS (MouseWheel); bazı X11: Button-4/5
        if getattr(event, "num", None) == 4:
            canvas.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5:
            canvas.yview_scroll(1, "units")
        else:
            delta = getattr(event, "delta", 0)
            # macOS’ta delta küçük adımlı olabilir
            step = int(-1 * (delta / 120)) if abs(delta) >= 120 else int(-1 * delta)
            if step == 0 and delta:
                step = -1 if delta > 0 else 1
            canvas.yview_scroll(step, "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    canvas.bind_all("<Button-4>", _on_mousewheel)
    canvas.bind_all("<Button-5>", _on_mousewheel)

    body = tk.Frame(content, bg=C_BG)
    body.pack(fill="both", expand=True, padx=22, pady=16)

    # --- 1 Genel ---
    s1 = _section(body, "1. Program ne işe yarar?", icons, "circle-question")
    _p(
        s1,
        "Excel’deki satırları okuyarak Xprinter (TSPL) yazıcıya seri barkod "
        "etiketi basar. Tek tek kopyala-yapıştır yapmadan toplu ve seçmeli baskı alır.",
    )
    _p(s1, "Öne çıkan yetenekler", bold=True)
    _chip_row(
        s1,
        [
            "Özel Excel başlıkları",
            "Seri üretimi",
            "QR / barkod tipi",
            "Liste arama",
            "Marka damgası",
            "Canlı önizleme",
        ],
    )

    # --- 2 Excel ---
    s2 = _section(body, "2. Excel’i nasıl hazırlarsınız?", icons, "file-excel")
    _p(s2, "Dosya ve başlık satırı", bold=True)
    _bullet(s2, ".xlsx veya .xlsm kullanın (örnek: Barkod.xlsx).")
    _bullet(s2, "1. satır sütun başlığıdır; veri 2. satırdan başlar.")
    _bullet(
        s2,
        "1. satırdaki isimler programda tablo, liste başlığı ve font etiketlerine yansır. "
        "İstediğiniz adı yazabilirsiniz.",
    )
    _bullet(s2, "Boş satırlar atlanır. Ana barkodu boş olan satırlar basılmaz.")

    _p(s2, "Sütun rolleri (varsayılan A → D)", bold=True)
    _bullet(s2, "A — Ana barkod (zorunlu). Tip: Code128 / 39 / 93 / EAN / QR.")
    _bullet(s2, "B — İkinci barkod (opsiyonel; doluysa basılır).")
    _bullet(s2, "C — Orta metin (ör. stok / malzeme no).")
    _bullet(s2, "D — Alt metin (ör. model / parça adı).")

    chip = tk.Frame(s2, bg=C_CHIP)
    chip.pack(fill="x", pady=(6, 4))
    chip_in = tk.Frame(chip, bg=C_CHIP)
    chip_in.pack(fill="x", padx=10, pady=8)
    tk.Label(
        chip_in,
        text="Örnek özel başlık satırı",
        font=("Segoe UI", 8),
        fg=C_MUTED,
        bg=C_CHIP,
        anchor="w",
    ).pack(anchor="w")
    tk.Label(
        chip_in,
        text="Seri No  |  Lot Barkod  |  Stok Kodu  |  Ürün Adı",
        font=("Consolas", 10),
        fg=C_NAVY,
        bg=C_CHIP,
        anchor="w",
    ).pack(anchor="w", pady=(2, 0))

    _p(
        s2,
        "Bilinen başlıklar (Barkod, A-K Barkod, ItemNo, ParcaAd, SeriNo…) farklı "
        "sütun sırasındaysa da tanınır. Tamamen özel isimlerde A–D sırası kullanılır.",
        muted=True,
    )

    # --- 3 Arayüz ---
    s3 = _section(body, "3. Arayüzde neler var?", icons, "window-maximize")
    _p(s3, "Üst alan", bold=True)
    _bullet(s3, "Excel yolu · Seç… · Yükle · Seri Üret…")
    _bullet(s3, "Yazıcı listesi · Yenile")
    _p(s3, "Ayarlar", bold=True)
    _bullet(s3, "Etiket: genişlik, yükseklik, gap, kopya, yoğunluk, barkod yükseklikleri")
    _bullet(
        s3,
        "Barkod tipi: ana ve 2. barkod için Code 128, Code 39, Code 93, EAN-13, EAN-8, QR Kod",
    )
    _bullet(s3, "Fontlar: ana barkod / 2. barkod / metin satırları ayrı boyutta")
    _bullet(s3, "Markalama: her etikete üst veya alt damga (örn. şirket adı)")
    _p(s3, "Liste ve önizleme", bold=True)
    _bullet(s3, "Sol liste: Excel veya seri üretim satırları")
    _bullet(s3, "Ara kutusu: listede anında filtre")
    _bullet(s3, "Listeyi temizle: tüm etiketleri listeden siler")
    _bullet(s3, "Sağ önizleme: Görsel + TSPL sekmeleri")
    _p(s3, "Alt butonlar", bold=True)
    _bullet(s3, "Test Baskı · Seçilileri Bas · Tümünü Bas · Ayarları Kaydet · Kullanım · Hakkında")

    # --- 3b Seri ---
    s3b = _section(body, "3b. Otomatik seri üretimi", icons, "wand-magic-sparkles")
    _p(
        s3b,
        "Excel olmadan da etiket üretebilirsiniz. Üstteki Seri Üret… ile önek, "
        "başlangıç numarası, adet, adım, sonek ve sıfır doldurma ayarlayın.",
    )
    _bullet(s3b, "Örnek: önek BYK-, başlangıç 1, adet 10, pad 4 → BYK-0001 … BYK-0010")
    _bullet(s3b, "İsteğe bağlı sabit orta/alt metin ve 2. barkod önek/sonek")
    _bullet(s3b, "Listeyi değiştir veya mevcut listenin sonuna ekle")
    _bullet(s3b, "En fazla 5000 satır; büyük listelerde Ara ile daraltın")

    # --- 3c Barkod tipleri ---
    s3c = _section(body, "3c. Barkod tipleri ve QR", icons, "qrcode")
    _p(
        s3c,
        "Ayarlar satırında Ana barkod tipi ve 2. barkod tipi ayrı seçilir. "
        "Önizleme ve TSPL komutları seçime göre üretilir.",
    )
    _bullet(s3c, "Code 128 — genel amaçlı (varsayılan)")
    _bullet(s3c, "Code 39 / Code 93 — endüstriyel / lojistik")
    _bullet(s3c, "EAN-13 / EAN-8 — perakende (sayısal veri; eksik basamaklar doldurulur)")
    _bullet(s3c, "QR Kod — kare kod; yükseklik (mm) alanı kare kenar olarak kullanılır")
    _p(
        s3c,
        "Not: EAN için veri rakamlardan oluşmalıdır. QR’da uzun metinler daha büyük "
        "sembol ister; kenarı büyütün veya etiketi büyütün.",
        muted=True,
    )

    # --- 4 Adımlar ---
    s4 = _section(body, "4. Adım adım kullanım", icons, "list-ol")
    _step(
        s4,
        "01",
        "Veri kaynağını seçin",
        "Excel: Seç… / Yükle — veya Excel’siz Seri Üret… ile numaralı liste oluşturun. "
        "Tablo başlıkları Excel 1. satırından gelir.",
    )
    _step(
        s4,
        "02",
        "Yazıcıyı seçin",
        "Xprinter XP-490B (veya TSPL/RAW yazıcınız). Görünmüyorsa Yenile; "
        "Windows veya macOS’ta yazıcı kurulu olmalıdır.",
    )
    _step(
        s4,
        "03",
        "Boyut, tip ve yoğunluğu ayarlayın",
        "98×98 mm varsayılan. Ana / 2. barkod tipini (128, 39, 93, EAN, QR) seçin. "
        "QR’da yükseklik = kare kenar (mm).",
    )
    _step(
        s4,
        "04",
        "Fontları ayarlayın",
        "Her alan için ayrı font (Küçük → Çok büyük). Etiketler Excel "
        "başlık adlarıyla güncellenir.",
    )
    _step(
        s4,
        "05",
        "Markalama (isteğe bağlı)",
        "Marka metni + Üst/Alt konum. Boş bırakırsanız damga basılmaz.",
    )
    _step(
        s4,
        "06",
        "Ara / filtreleyin (isteğe bağlı)",
        "Liste üstündeki Ara kutusuna yazarak satırları daraltın; "
        "yalnızca görünen satırlardan seçim yapıp basabilirsiniz.",
    )
    _step(
        s4,
        "07",
        "Önizlemeyi kontrol edin",
        "Satır seçin → Görsel sekmesi yerleşim, TSPL sekmesi yazıcı komutları.",
    )
    _step(
        s4,
        "08",
        "Baskı alın",
        "Test Baskı: örnek şablon.\n"
        "Seçilileri Bas: Ctrl ile çoklu seçim.\n"
        "Tümünü Bas: listedeki tüm etiketler (filtre açıkken yalnızca görünenler).",
    )
    _step(
        s4,
        "09",
        "Ayarları kaydedin",
        "Yazıcı, boyut, barkod tipi, font, marka ve sütun adları saklanır; "
        "sonraki açılışta aynı tercihlerle gelir.",
    )

    # --- 5 Yerleşim ---
    s5 = _section(body, "5. Etiket üzerindeki sıra", icons, "layer-group")
    _p(s5, "Kağıt üzerinde yukarıdan aşağı:")
    _bullet(s5, "Marka damgası (üst seçildiyse)")
    _bullet(s5, "Ana barkod / QR + insan okunur metin (ortalı)")
    _bullet(s5, "İkinci barkod / QR (varsa) + metni (ortalı)")
    _bullet(s5, "Orta metin (Excel 3. sütun)")
    _bullet(s5, "Alt metin (Excel 4. sütun)")
    _bullet(s5, "Marka damgası (alt seçildiyse)")

    # --- 6 Test ---
    s6 = _section(body, "6. Test Baskı (örnek)", icons, "flask")
    _p(
        s6,
        "Listedeki satırı değil; sabit örnek şablonu basar. Yazıcı ve yerleşimi "
        "doğrulamak içindir. Örnekte marka BYK PROJECT üstte basılır; "
        "uygulamadaki marka alanı kullanılmaz.",
    )

    # --- 7 Sorun ---
    s7 = _section(body, "7. Sık karşılaşılan durumlar", icons, "triangle-exclamation")
    _bullet(s7, "Liste boş: A sütunu dolu mu veya Seri Üret ile satır oluşturdunuz mu?")
    _bullet(s7, "Başlıklar eski kaldı: Excel’i yeniden Yükle’ye basın.")
    _bullet(s7, "Yazıcı yok: Windows Yazıcılar veya macOS Yazıcılar & Tarayıcılar’da XP-490B ekli olmalı.")
    _bullet(s7, "macOS baskı hatası: yazıcıyı yeniden ekleyin; uygulama raw (TSPL) gönderir.")
    _bullet(s7, "QR okunmuyor: kenarı (yükseklik mm) büyütün; yoğunluğu artırın.")
    _bullet(s7, "EAN hata: verinin rakam olduğundan emin olun.")
    _bullet(s7, "Barkod kayık / küçük: önizleme + font / yükseklik ayarı.")
    _bullet(s7, "2. barkod basılmıyor: B sütunu boşsa bilinçli olarak atlanır.")
    _bullet(s7, "Filtre sonrası az satır: Ara kutusunu temizleyin.")

    # --- 8 Destek ---
    s8 = _section(body, "8. Destek", icons, "headset")
    _bullet(s8, "E-posta: metin@biyik.dev")
    _bullet(s8, "Geliştirici: Metin Faruk BIYIK · BIYIK.DEV")

    footer = tk.Frame(win, bg=C_BG)
    footer.pack(fill="x", padx=22, pady=(0, 14))
    icon_button(
        footer, "Kapat", "circle-xmark", lambda: _close(), icons, fill=ICON_MUTED
    ).pack(side="right")
    tk.Label(
        footer,
        text="BIYIK.DEV  ·  Destek: metin@biyik.dev",
        font=("Segoe UI", 8),
        fg=C_MUTED,
        bg=C_BG,
    ).pack(side="left")

    def _close() -> None:
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            try:
                canvas.unbind_all(seq)
            except tk.TclError:
                pass
        win.destroy()

    win._photos = photos  # type: ignore[attr-defined]
    win._icons = icons  # type: ignore[attr-defined]
    win.protocol("WM_DELETE_WINDOW", _close)
    win.bind("<Escape>", lambda _e: _close())
    win.focus_set()
