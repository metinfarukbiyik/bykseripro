"""Yazıcıya RAW TSPL gönderimi — Windows (win32) ve macOS/Linux (CUPS)."""

from __future__ import annotations

import os
import platform
import subprocess
import tempfile
from pathlib import Path


def _is_windows() -> bool:
    return platform.system() == "Windows"


def _is_macos() -> bool:
    return platform.system() == "Darwin"


# ── Windows ──────────────────────────────────────────────────────────


def _win_list_printers() -> list[str]:
    try:
        import win32print
    except ImportError as exc:
        raise RuntimeError(
            "pywin32 yüklü değil. Kurulum: pip install pywin32"
        ) from exc

    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    printers = win32print.EnumPrinters(flags)
    names = [p[2] for p in printers]
    return sorted(set(names), key=str.lower)


def _win_default_printer() -> str:
    import win32print

    return win32print.GetDefaultPrinter()


def _win_send_raw(printer_name: str, raw: bytes, job_name: str) -> None:
    import win32print

    handle = win32print.OpenPrinter(printer_name)
    try:
        win32print.StartDocPrinter(handle, 1, (job_name, None, "RAW"))
        try:
            win32print.StartPagePrinter(handle)
            win32print.WritePrinter(handle, raw)
            win32print.EndPagePrinter(handle)
        finally:
            win32print.EndDocPrinter(handle)
    finally:
        win32print.ClosePrinter(handle)


# ── CUPS (macOS / Linux) ─────────────────────────────────────────────


def _cups_list_printers() -> list[str]:
    try:
        result = subprocess.run(
            ["lpstat", "-a"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "CUPS yazıcı sistemi bulunamadı (lpstat). "
            "macOS’ta Yazıcılar & Tarayıcılar’dan yazıcı ekleyin."
        ) from exc

    names: list[str] = []
    for line in (result.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        # "Printer_Name accepting requests since ..."
        name = line.split()[0]
        if name:
            names.append(name)
    return sorted(set(names), key=str.lower)


def _cups_default_printer() -> str:
    try:
        result = subprocess.run(
            ["lpstat", "-d"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return ""

    text = (result.stdout or "").strip()
    # "system default destination: Name"
    if ":" in text:
        return text.split(":", 1)[1].strip()
    return ""


def _cups_send_raw(printer_name: str, raw: bytes, job_name: str) -> None:
    """TSPL’i CUPS kuyruğuna raw olarak gönder (lp -o raw)."""
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix="biyik_tspl_",
            suffix=".tspl",
            delete=False,
        ) as tmp:
            tmp.write(raw)
            tmp_path = tmp.name

        cmd = [
            "lp",
            "-d",
            printer_name,
            "-o",
            "raw",
            "-t",
            job_name[:80] or "Label",
            tmp_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            # Bazı kuyruklarda -o raw reddedilir; düz lp dene
            cmd2 = ["lp", "-d", printer_name, "-t", job_name[:80] or "Label", tmp_path]
            result2 = subprocess.run(cmd2, capture_output=True, text=True, check=False)
            if result2.returncode != 0:
                err = (result.stderr or result.stdout or "").strip()
                err2 = (result2.stderr or result2.stdout or "").strip()
                raise RuntimeError(
                    "Yazıcıya gönderilemedi.\n"
                    f"Komut: lp -o raw → {err or 'hata'}\n"
                    f"Komut: lp → {err2 or 'hata'}\n\n"
                    "macOS: Yazıcılar & Tarayıcılar’da Xprinter’ı ekleyin; "
                    "mümkünse ‘Generic’ / raw uyumlu sürücü kullanın."
                )
    finally:
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass


# ── Ortak API ─────────────────────────────────────────────────────────


def list_printers() -> list[str]:
    if _is_windows():
        return _win_list_printers()
    return _cups_list_printers()


def default_printer() -> str:
    if _is_windows():
        try:
            return _win_default_printer()
        except Exception:
            printers = _win_list_printers()
            return printers[0] if printers else ""
    name = _cups_default_printer()
    if name:
        return name
    printers = _cups_list_printers()
    return printers[0] if printers else ""


def send_raw(
    printer_name: str, data: bytes | str, job_name: str = "XP490B Label"
) -> None:
    """TSPL komutlarını yazıcıya RAW olarak gönderir."""
    if isinstance(data, str):
        raw = data.encode("utf-8", errors="replace")
    else:
        raw = data

    if not printer_name:
        printer_name = default_printer()
    if not printer_name:
        raise RuntimeError("Yazıcı seçilmedi ve varsayılan yazıcı bulunamadı.")

    if _is_windows():
        _win_send_raw(printer_name, raw, job_name)
    else:
        _cups_send_raw(printer_name, raw, job_name)


def platform_print_hint() -> str:
    """Kullanıcıya kısa platform ipucu."""
    if _is_windows():
        return "Windows: yazıcı TSPL/RAW sürücü ile kurulu olmalı."
    if _is_macos():
        return (
            "macOS: Yazıcılar & Tarayıcılar’dan Xprinter’ı ekleyin; "
            "baskı CUPS üzerinden raw gönderilir."
        )
    return "Linux: CUPS’ta yazıcı tanımlı olmalı (lpstat -a)."
