"""Kullanım kılavuzu — sade, adım adım; ana pencereyle aynı görünüm."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageTk

from app_icon import apply_app_icon
from paths import assets_dir
from theme import BLUE, CARD, CARD_BORDER, GOLD, MUTED, NAVY, PAGE, TEXT
from ui_icons import IconStore, icon_button, titled_label

ASSETS = assets_dir()

C_TIP = "#EEF4FD"
C_TIP_EDGE = "#C9DAF6"
C_PROBLEM = "#B4232C"
WRAP = 520


def _load_photo(path: Path, size: int, store: list) -> ImageTk.PhotoImage | None:
    if not path.exists():
        return None
    img = Image.open(path).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
    photo = ImageTk.PhotoImage(img)
    store.append(photo)
    return photo


# ── Yapı taşları ─────────────────────────────────────────────────────


def _section(parent: tk.Frame, title: str, icon: str, icons: IconStore, lead: str = "") -> tk.Frame:
    """Başlık kartın üstünde, içerik beyaz kartta (ana penceredeki gibi)."""
    titled_label(
        parent, title, icon, icons, size=15, fill=BLUE,
        font=("Segoe UI Semibold", 12), bg=PAGE, fg=NAVY,
    ).pack(fill="x", pady=(6, 2))
    if lead:
        tk.Label(
            parent, text=lead, font=("Segoe UI", 9), fg=MUTED, bg=PAGE,
            wraplength=WRAP + 40, justify="left", anchor="w",
        ).pack(fill="x", pady=(0, 6))
    box = tk.Frame(parent, bg=CARD, highlightbackground=CARD_BORDER, highlightthickness=1)
    box.pack(fill="x", pady=(0, 16))
    inner = tk.Frame(box, bg=CARD)
    inner.pack(fill="x", padx=16, pady=12)
    return inner


def _text(parent: tk.Frame, text: str, *, muted: bool = False, bold: bool = False) -> None:
    tk.Label(
        parent, text=text,
        font=("Segoe UI Semibold", 10) if bold else ("Segoe UI", 10),
        fg=MUTED if muted else TEXT, bg=parent.cget("bg"),
        wraplength=WRAP, justify="left", anchor="w",
    ).pack(fill="x", pady=(0, 6))


def _step(parent: tk.Frame, num: int, title: str, detail: str) -> None:
    """Numaralı adım: mavi daire + başlık + açıklama."""
    row = tk.Frame(parent, bg=CARD)
    row.pack(fill="x", pady=5)
    badge = tk.Canvas(row, width=28, height=28, bg=CARD, highlightthickness=0)
    badge.create_oval(2, 2, 26, 26, fill=BLUE, outline=BLUE)
    badge.create_text(14, 14, text=str(num), fill="#FFFFFF", font=("Segoe UI Semibold", 10))
    badge.pack(side="left", anchor="n", padx=(0, 12))
    col = tk.Frame(row, bg=CARD)
    col.pack(side="left", fill="x", expand=True)
    tk.Label(
        col, text=title, font=("Segoe UI Semibold", 10), fg=NAVY, bg=CARD, anchor="w",
    ).pack(fill="x")
    tk.Label(
        col, text=detail, font=("Segoe UI", 9), fg=TEXT, bg=CARD,
        wraplength=WRAP - 40, justify="left", anchor="w",
    ).pack(fill="x", pady=(1, 0))


def _item(parent: tk.Frame, name: str, detail: str) -> None:
    """Kalın ad + açıklama satırı."""
    row = tk.Frame(parent, bg=CARD)
    row.pack(fill="x", pady=3)
    tk.Label(row, text="•", font=("Segoe UI", 10), fg=GOLD, bg=CARD).pack(side="left", anchor="n")
    tk.Label(
        row, text=name, font=("Segoe UI Semibold", 9), fg=NAVY, bg=CARD, anchor="nw",
    ).pack(side="left", anchor="n", padx=(6, 6))
    tk.Label(
        row, text=detail, font=("Segoe UI", 9), fg=TEXT, bg=CARD,
        wraplength=WRAP - 150, justify="left", anchor="w",
    ).pack(side="left", fill="x", expand=True)


def _table(parent: tk.Frame, rows: list[tuple[str, str, str]]) -> None:
    """Excel sütun tablosu: sütun · rol · zorunlu mu."""
    grid = tk.Frame(parent, bg=CARD_BORDER)
    grid.pack(fill="x", pady=(2, 8))
    for r, cells in enumerate(rows):
        head = r == 0
        for c, value in enumerate(cells):
            tk.Label(
                grid, text=value,
                font=("Segoe UI Semibold", 9) if head else ("Segoe UI", 9),
                fg=NAVY if head else TEXT, bg="#F1F5FB" if head else CARD,
                anchor="w", padx=10, pady=5,
            ).grid(row=r, column=c, sticky="nsew", padx=(0 if c == 0 else 1, 0), pady=(0 if r == 0 else 1, 0))
    for c, w in enumerate((1, 3, 1)):
        grid.columnconfigure(c, weight=w)


def _tip(parent: tk.Frame, text: str) -> None:
    box = tk.Frame(parent, bg=C_TIP, highlightbackground=C_TIP_EDGE, highlightthickness=1)
    box.pack(fill="x", pady=(4, 2))
    tk.Label(
        box, text=f"İpucu:  {text}", font=("Segoe UI", 9), fg=NAVY, bg=C_TIP,
        wraplength=WRAP - 20, justify="left", anchor="w", padx=10, pady=7,
    ).pack(fill="x")


def _problem(parent: tk.Frame, problem: str, solution: str) -> None:
    row = tk.Frame(parent, bg=CARD)
    row.pack(fill="x", pady=4)
    tk.Label(
        row, text=problem, font=("Segoe UI Semibold", 9), fg=C_PROBLEM, bg=CARD, anchor="w",
    ).pack(fill="x")
    tk.Label(
        row, text=f"→ {solution}", font=("Segoe UI", 9), fg=TEXT, bg=CARD,
        wraplength=WRAP, justify="left", anchor="w",
    ).pack(fill="x", padx=(10, 0))


# ── Pencere ──────────────────────────────────────────────────────────


def open_help(parent: tk.Tk | tk.Toplevel, app_title: str) -> None:
    """Kullanım kılavuzu."""
    win = tk.Toplevel(parent)
    win.title("Kullanım Kılavuzu")
    apply_app_icon(win)
    win.configure(bg=PAGE)
    win.resizable(True, True)
    win.minsize(600, 520)
    win.transient(parent)
    win.grab_set()

    width = 640
    height = min(760, max(560, parent.winfo_height() - 40))
    bar = max(0, parent.winfo_rooty() - parent.winfo_y())
    px = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
    py = parent.winfo_rooty() + (parent.winfo_height() - height) // 2 - bar
    win.geometry(f"{width}x{height}+{max(0, px)}+{max(0, py)}")

    photos: list[ImageTk.PhotoImage] = []
    icons = IconStore()

    # Lacivert başlık bandı (ana pencereyle aynı)
    header = tk.Frame(win, bg=NAVY)
    header.pack(fill="x")
    head_inner = tk.Frame(header, bg=NAVY)
    head_inner.pack(fill="x", padx=22, pady=14)
    badge = _load_photo(ASSETS / "biyik_badge.png", 44, photos)
    if badge:
        tk.Label(head_inner, image=badge, bg=NAVY).pack(side="left", padx=(0, 12))
    titles = tk.Frame(head_inner, bg=NAVY)
    titles.pack(side="left")
    titled_label(
        titles, "Kullanım Kılavuzu", "book-open", icons, size=17, fill="#FFFFFF",
        font=("Segoe UI Semibold", 15), bg=NAVY, fg="#FFFFFF",
    ).pack(anchor="w")
    tk.Label(
        titles, text=f"{app_title}  ·  Excel’den etikete, 5 adımda",
        font=("Segoe UI", 9), fg="#E2C66F", bg=NAVY, anchor="w",
    ).pack(anchor="w", pady=(2, 0))
    tk.Frame(win, bg=GOLD, height=3).pack(fill="x")

    # Alt çubuk (kaydırılan alanın dışında)
    footer = tk.Frame(win, bg=PAGE)
    footer.pack(side="bottom", fill="x", padx=22, pady=(6, 12))
    tk.Label(
        footer, text="Destek: metin@biyik.dev", font=("Segoe UI", 9), fg=MUTED, bg=PAGE,
    ).pack(side="left")

    # Kaydırılabilir içerik
    shell = tk.Frame(win, bg=PAGE)
    shell.pack(fill="both", expand=True)
    canvas = tk.Canvas(shell, bg=PAGE, highlightthickness=0)
    scroll = ttk.Scrollbar(
        shell, orient="vertical", command=canvas.yview, style="Page.Vertical.TScrollbar"
    )
    canvas.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    content = tk.Frame(canvas, bg=PAGE)
    win_id = canvas.create_window((0, 0), window=content, anchor="nw")

    def _on_configure(_e=None) -> None:
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfigure(win_id, width=canvas.winfo_width())

    content.bind("<Configure>", _on_configure)
    canvas.bind("<Configure>", _on_configure)

    def _on_mousewheel(event) -> None:
        if getattr(event, "num", None) == 4:
            canvas.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5:
            canvas.yview_scroll(1, "units")
        else:
            delta = getattr(event, "delta", 0)
            # Windows 120'lik adımlar, macOS küçük adımlar gönderir
            step = int(-delta / 120) if abs(delta) >= 120 else -delta
            if step == 0 and delta:
                step = -1 if delta > 0 else 1
            canvas.yview_scroll(step, "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    canvas.bind_all("<Button-4>", _on_mousewheel)
    canvas.bind_all("<Button-5>", _on_mousewheel)

    body = tk.Frame(content, bg=PAGE)
    body.pack(fill="both", expand=True, padx=22, pady=(14, 4))

    # 1 — Hızlı başlangıç
    s = _section(
        body, "Hızlı başlangıç", "rocket", icons,
        "İlk baskınız için bu beş adım yeterli.",
    )
    _step(s, 1, "Excel’i yükleyin", "Üstte “Seç…” ile dosyanızı seçin, ardından “Yükle”. "
          "Excel’iniz yoksa “Seri Üret…” ile numaralı liste oluşturabilirsiniz.")
    _step(s, 2, "Yazıcıyı ve DPI’yı seçin", "Etiket yazıcınızı listeden seçin. Altında yeşil ✓ "
          "görüyorsanız uyumludur. DPI, yazıcının etiketinde yazar (genelde 203 veya 300).")
    _step(s, 3, "Etiket ölçüsünü girin", "“Etiket ve barkod” sekmesinde genişlik ve yüksekliği "
          "mm olarak yazın (ör. 100 × 40).")
    _step(s, 4, "Önizlemeye bakın", "Sağdaki önizleme kağıtta çıkacak görüntünün aynısıdır. "
          "Kırmızı çerçeve görürseniz içerik sığmıyor demektir (bkz. Etiketi düzenleme).")
    _step(s, 5, "Önce deneyin, sonra basın", "“Test Baskı” ile bir örnek alın. Her şey yerindeyse "
          "“Seçilileri Bas” ya da “Tümünü Bas”. Son olarak “Ayarları Kaydet”.")

    # 2 — Excel
    s = _section(
        body, "Excel dosyası", "file-excel", icons,
        "İlk satır başlıktır; sonraki her satır bir etiket olur.",
    )
    _table(s, [
        ("Sütun", "Etikette", ""),
        ("1.", "Ana barkod / seri no", "zorunlu"),
        ("2.", "İkinci barkod", "isteğe bağlı"),
        ("3.", "Orta metin (ör. stok kodu)", "isteğe bağlı"),
        ("4.", "Alt metin (ör. ürün adı)", "isteğe bağlı"),
    ])
    _text(s, "Başlık adlarını istediğiniz gibi yazabilirsiniz. İkinci barkod sütununuz "
          "“A-K Barkod”, “M Barkod” ya da “C Barkod” olabilir; adında “barkod” geçen ikinci "
          "sütun otomatik tanınır.", muted=True)
    _text(s, "Boş satırlar ve ana barkodu boş olan satırlar atlanır.", muted=True)

    # 3 — Liste
    s = _section(body, "Listeyle çalışma", "table-list", icons)
    _item(s, "Ara", "Yazdıkça liste süzülür. “Tümünü Bas” yalnızca görünen satırları basar.")
    _item(s, "Seri ekle…", "Excel’i açmadan listeye tek seri ekleyin.")
    _item(s, "Seçilileri çıkar", "Yanlış satırı listeden çıkarın (Delete tuşu ya da sağ tık). "
          "Excel dosyanız değişmez.")
    _item(s, "Geri al", "Yanlışlıkla çıkardığınızı geri getirin: Ctrl+Z (Mac’te ⌘+Z).")
    _item(s, "Çoklu seçim", "Ctrl (Mac’te ⌘) ya da Shift ile birden çok satır seçin.")
    _item(s, "Seri Üret…", "Önek + sayı + sonek ile liste oluşturur (ör. BYK-0001 … BYK-0100).")

    # 4 — Etiketi düzenleme
    s = _section(body, "Etiketi düzenleme", "sliders", icons)
    _item(s, "Etiket ve barkod", "Ölçü, DPI, kopya, yoğunluk, barkod yüksekliği ve tipi "
          "(Code 128, Code 39/93, EAN, QR).")
    _item(s, "Fontlar ve markalama", "Yazı boyutları. “Marka bas” işaretliyse firma adınız "
          "seçtiğiniz konum ve stille (düz, çerçeveli, siyah bant, çizgili) basılır.")
    _item(s, "Yerleşim ayarları…", "Önizlemenin altındaki düğme ya da önizlemeye çift tık. "
          "Her öğenin boyutu, hizası (sol/orta/sağ), çizgi kalınlığı ve boşlukları ayrı ayarlanır.")
    _item(s, "Elle yerleştirme", "Yerleşim penceresindeki önizlemede bir öğeye tıklayıp "
          "sürükleyin; ortaya yaklaşınca kendiliğinden ortalanır. Ok tuşlarıyla 0,5 mm "
          "(Shift ile 2 mm) kaydırın, çift tıkla konumu sıfırlayın, Ctrl/⌘+Z ile geri alın.")
    _tip(s, "Etikete sığmayan öğe kırmızı çerçeveyle gösterilir. “Sorunları otomatik "
         "düzelt” düğmesi taşan öğeyi yerine alır, gerekirse 2. barkodu yan yana koyar ve "
         "boşluk / yazı / barkod boyutunu küçültür.")

    # 5 — Sorunlar
    s = _section(body, "Sorun mu var?", "circle-question", icons)
    _problem(s, "Yazıcı listede görünmüyor",
             "Yazıcının bilgisayarda kurulu olduğundan emin olun, sonra “Yenile”ye basın.")
    _problem(s, "Etiket kaymış, çok büyük ya da çok küçük çıkıyor",
             "Seçili DPI yazıcınızınkiyle uyuşmuyor (ör. 203 DPI yazıcıda 300 seçili). "
             "Yazıcı adının altındaki satır uyarır; program DPI’yı sürücüden okuyabiliyorsa "
             "kendisi ayarlar. Değilse yazıcının etiketindeki değeri (203 / 300) seçin.")
    _problem(s, "Anlamsız karakterler basılıyor",
             "Yazıcınız TSPL desteklemiyor olabilir (Zebra, Godex, Brother, DYMO). "
             "Yazıcı adının altındaki uyarıya bakın.")
    _problem(s, "Baskı kağıtta kayık",
             "Yerleşim ayarları → Yazıcı kalibrasyonu ile mm cinsinden kaydırın.")
    _problem(s, "Metinler bozuk ya da eksik",
             "Yerleşim ayarları → Metin basımı → “Yazıcı fontu”nu deneyin.")
    _problem(s, "QR ya da barkod okunmuyor",
             "Barkod yüksekliğini (QR’da kenarı) büyütün, yoğunluğu artırın. EAN için veri "
             "yalnızca rakam olmalıdır.")

    # 6 — Güncelleme ve destek
    s = _section(body, "Güncelleme ve destek", "headset", icons)
    _text(s, "Program açılışta yeni sürümü kendisi kontrol eder. Yeni sürüm varsa "
          "“Güncelleme geldi” penceresi çıkar; “Şimdi güncelle” deyin, ayarlarınız korunur. "
          "Üstteki “Güncelleme” düğmesiyle istediğiniz zaman kontrol edebilirsiniz.")
    _text(s, "Yardım için: metin@biyik.dev  ·  Hakkında penceresinden WhatsApp ile de "
          "ulaşabilirsiniz.", muted=True)

    def _close() -> None:
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            try:
                canvas.unbind_all(seq)
            except tk.TclError:
                pass
        win.destroy()

    icon_button(
        footer, "Kapat", "circle-xmark", _close, icons, fill="#FFFFFF", style="Primary.TButton",
    ).pack(side="right")

    win._photos = photos  # type: ignore[attr-defined]
    win._icons = icons  # type: ignore[attr-defined]
    win.protocol("WM_DELETE_WINDOW", _close)
    win.bind("<Escape>", lambda _e: _close())
    win.focus_set()
