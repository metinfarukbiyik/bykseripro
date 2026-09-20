"""Otomatik seri / barkod üretimi penceresi."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app_icon import apply_app_icon
from tspl_builder import LabelData
from ui_icons import C_MUTED, C_NAVY, IconStore, icon_button


def generate_serial_labels(
    *,
    prefix: str,
    start: int,
    count: int,
    suffix: str = "",
    pad: int = 0,
    step: int = 1,
    item_no: str = "",
    parca_ad: str = "",
    ak_same: bool = False,
    ak_prefix: str = "",
    ak_suffix: str = "",
) -> list[LabelData]:
    """Başlangıç + adet ile seri etiket listesi üretir."""
    if count < 1:
        raise ValueError("Adet en az 1 olmalı.")
    if step == 0:
        raise ValueError("Adım 0 olamaz.")
    pad = max(0, int(pad))
    labels: list[LabelData] = []
    value = int(start)
    for _ in range(int(count)):
        num = str(value)
        if pad:
            num = num.zfill(pad)
        barkod = f"{prefix}{num}{suffix}"
        if ak_same:
            ak = barkod
        else:
            ak_num = num
            ak = f"{ak_prefix}{ak_num}{ak_suffix}" if (ak_prefix or ak_suffix) else ""
        labels.append(
            LabelData(
                barkod=barkod,
                ak_barkod=ak,
                item_no=item_no,
                parca_ad=parca_ad,
            )
        )
        value += int(step)
    return labels


def open_serial_dialog(
    parent: tk.Tk | tk.Toplevel,
) -> tuple[list[LabelData], str] | None:
    """Seri üretim diyaloğu. (labels, mode) veya None. mode: replace|append."""
    win = tk.Toplevel(parent)
    win.title("Otomatik Seri Üretimi")
    apply_app_icon(win)
    win.transient(parent)
    win.grab_set()
    win.resizable(False, False)

    icons = IconStore()
    result: dict = {"labels": None, "mode": "replace"}

    pad = {"padx": 8, "pady": 4}
    body = ttk.Frame(win, padding=(12, 12, 12, 16))
    body.pack(fill="both", expand=True)

    ttk.Label(
        body,
        text="Önek + sayı + sonek ile otomatik barkod listesi oluşturur.",
        wraplength=420,
    ).grid(row=0, column=0, columnspan=4, sticky="w", **pad)

    prefix_var = tk.StringVar(value="")
    start_var = tk.StringVar(value="1")
    count_var = tk.StringVar(value="10")
    step_var = tk.StringVar(value="1")
    suffix_var = tk.StringVar(value="")
    pad_var = tk.StringVar(value="4")
    item_var = tk.StringVar(value="")
    parca_var = tk.StringVar(value="")
    ak_same_var = tk.BooleanVar(value=False)
    ak_prefix_var = tk.StringVar(value="")
    ak_suffix_var = tk.StringVar(value="")
    preview_var = tk.StringVar(value="")

    def _refresh_preview(*_a) -> None:
        try:
            start = int(start_var.get().strip() or "0")
            count = max(1, min(50, int(count_var.get().strip() or "1")))
            step = int(step_var.get().strip() or "1")
            pad_n = int(pad_var.get().strip() or "0")
            sample = generate_serial_labels(
                prefix=prefix_var.get(),
                start=start,
                count=min(3, count),
                suffix=suffix_var.get(),
                pad=pad_n,
                step=step,
                item_no=item_var.get().strip(),
                parca_ad=parca_var.get().strip(),
                ak_same=ak_same_var.get(),
                ak_prefix=ak_prefix_var.get(),
                ak_suffix=ak_suffix_var.get(),
            )
            preview_var.set("Örnek: " + " , ".join(x.barkod for x in sample))
        except Exception:
            preview_var.set("Örnek: —")

    fields = [
        (1, "Önek", prefix_var),
        (2, "Başlangıç", start_var),
        (3, "Adet", count_var),
        (4, "Adım", step_var),
        (5, "Sonek", suffix_var),
        (6, "Sıfır doldurma", pad_var),
        (7, "ItemNo / orta metin", item_var),
        (8, "ParcaAd / alt metin", parca_var),
    ]
    for row, label, var in fields:
        ttk.Label(body, text=label + ":").grid(row=row, column=0, sticky="e", **pad)
        ent = ttk.Entry(body, textvariable=var, width=28)
        ent.grid(row=row, column=1, columnspan=3, sticky="ew", **pad)
        var.trace_add("write", _refresh_preview)

    ttk.Checkbutton(
        body,
        text="2. barkodu ana barkod ile aynı yap",
        variable=ak_same_var,
        command=_refresh_preview,
    ).grid(row=9, column=0, columnspan=4, sticky="w", **pad)

    ttk.Label(body, text="2. barkod önek:").grid(row=10, column=0, sticky="e", **pad)
    ttk.Entry(body, textvariable=ak_prefix_var, width=12).grid(
        row=10, column=1, sticky="w", **pad
    )
    ttk.Label(body, text="sonek:").grid(row=10, column=2, sticky="e", **pad)
    ttk.Entry(body, textvariable=ak_suffix_var, width=12).grid(
        row=10, column=3, sticky="w", **pad
    )
    ak_prefix_var.trace_add("write", _refresh_preview)
    ak_suffix_var.trace_add("write", _refresh_preview)

    ttk.Label(body, textvariable=preview_var, foreground="#2A5A8C").grid(
        row=11, column=0, columnspan=4, sticky="w", **pad
    )

    mode_var = tk.StringVar(value="replace")
    mode_fr = ttk.Frame(body)
    mode_fr.grid(row=12, column=0, columnspan=4, sticky="w", pady=(8, 4))
    ttk.Radiobutton(
        mode_fr, text="Listeyi değiştir", variable=mode_var, value="replace"
    ).pack(side="left", padx=(0, 12))
    ttk.Radiobutton(
        mode_fr, text="Listenin sonuna ekle", variable=mode_var, value="append"
    ).pack(side="left")

    actions = ttk.Frame(body)
    actions.grid(row=13, column=0, columnspan=4, sticky="e", pady=(12, 4))

    def _cancel() -> None:
        result["labels"] = None
        win.destroy()

    def _ok() -> None:
        try:
            start = int(start_var.get().strip())
            count = int(count_var.get().strip())
            step = int(step_var.get().strip() or "1")
            pad_n = int(pad_var.get().strip() or "0")
            if count < 1 or count > 5000:
                raise ValueError("Adet 1–5000 arasında olmalı.")
            labels = generate_serial_labels(
                prefix=prefix_var.get(),
                start=start,
                count=count,
                suffix=suffix_var.get(),
                pad=pad_n,
                step=step,
                item_no=item_var.get().strip(),
                parca_ad=parca_var.get().strip(),
                ak_same=ak_same_var.get(),
                ak_prefix=ak_prefix_var.get(),
                ak_suffix=ak_suffix_var.get(),
            )
        except Exception as exc:
            messagebox.showerror("Seri üretimi", str(exc), parent=win)
            return
        result["labels"] = labels
        result["mode"] = mode_var.get()
        win.destroy()

    icon_button(actions, "İptal", "xmark", _cancel, icons, fill=C_MUTED).pack(
        side="right", padx=4
    )
    icon_button(actions, "Üret", "wand-magic-sparkles", _ok, icons, fill=C_NAVY).pack(
        side="right", padx=4
    )

    body.columnconfigure(1, weight=1)
    _refresh_preview()

    # İçeriğe göre boyutla; sabit yükseklik butonları kesiyordu.
    win.update_idletasks()
    width = max(460, win.winfo_reqwidth())
    height = win.winfo_reqheight()
    win.geometry(f"{width}x{height}")
    win.update_idletasks()
    px = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
    py = parent.winfo_rooty() + max(0, (parent.winfo_height() - height) // 2)
    win.geometry(f"+{max(0, px)}+{max(0, py)}")

    win.protocol("WM_DELETE_WINDOW", _cancel)
    win.bind("<Escape>", lambda _e: _cancel())
    win.wait_window()

    if result["labels"] is None:
        return None
    return list(result["labels"]), str(result["mode"])
