"""
Yazıcı uyumluluk denetimi — yazıcı adına göre TSPL desteğini tahmin eder.

Program etiketleri TSPL/TSPL2 komutlarıyla RAW gönderir. TSPL; Xprinter, TSC,
Gprinter, HPRT, iDPRT, Rongta, Munbyn vb. termal etiket yazıcılarının çoğunda
bulunur. Zebra (ZPL), Godex (EZPL), Brother, DYMO gibi farklı dil kullanan
yazıcılar ve normal ofis yazıcıları bu komutları anlamaz.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

OK = "ok"
WARN = "warn"
UNKNOWN = "unknown"


@dataclass(frozen=True)
class PrinterCheck:
    status: str  # ok | warn | unknown
    message: str


# (desen, marka adı) — TSPL / TSPL2 destekleyen bilinen etiket yazıcıları
_TSPL = (
    (r"xprinter|\bxp[-_ ]?\d", "Xprinter"),
    (r"\btsc\b|\bttp[-_ ]?\d|\bte\d{3}|\bta\d{3}|\bda\d{3}|\bme\d{3}|\bmh\d{3}", "TSC"),
    (r"gprinter|\bgp[-_ ]?\d", "Gprinter"),
    (r"hprt|\bht\d{3}", "HPRT"),
    (r"idprt|\bid\d{3}|\bsp\d{3}", "iDPRT"),
    (r"rongta|\brp\d{3}", "Rongta"),
    (r"munbyn|\bitpp\d", "Munbyn"),
    (r"zenpert|beeprt|arkscan|polono|jadens|nelko|phomemo|vretti|\bdeli\b", "TSPL uyumlu"),
)

# Genel adlı etiket yazıcıları — büyük ihtimalle TSPL, ama marka bilinmiyor
_GENERIC_LABEL = r"label\s*printer|barcode\s*printer|thermal|etiket|4barcode|4b-\d"

# (desen, açıklama) — TSPL anlamayan yazıcılar
_NOT_TSPL = (
    (r"zebra|\bzd\d{3}|\bgk\d{3}|\bgx\d{3}|\bzt\d{3}|\blp\s?2844", "Zebra yazıcılar ZPL/EPL kullanır"),
    (r"godex", "Godex yazıcılar EZPL kullanır"),
    (r"brother|\bql[-_ ]?\d|\btd[-_ ]?\d|p-?touch", "Brother etiket yazıcıları TSPL desteklemez"),
    (r"dymo|labelwriter", "DYMO yazıcılar TSPL desteklemez"),
    (r"honeywell|intermec|datamax|\bsato\b|citizen|bixolon", "Bu marka farklı bir yazıcı dili kullanır"),
    (
        r"pdf|xps|onenote|fax|send to|microsoft print",
        "Bu bir sanal yazıcı; etiket yazıcısı değil",
    ),
    (
        r"\bhp\b|laserjet|deskjet|officejet|canon|epson|kyocera|ricoh|xerox|lexmark|samsung",
        "Normal ofis yazıcısı; termal etiket yazıcısı değil",
    ),
)


def check_printer(name: str) -> PrinterCheck:
    raw = (name or "").strip()
    if not raw:
        return PrinterCheck(WARN, "Yazıcı seçilmedi.")
    low = raw.lower()
    for pattern, reason in _NOT_TSPL:
        if re.search(pattern, low):
            return PrinterCheck(
                WARN,
                f"{reason}. Bu program TSPL komutu gönderir; baskı çıkmayabilir "
                "veya anlamsız karakterler basılabilir.",
            )
    for pattern, brand in _TSPL:
        if re.search(pattern, low):
            return PrinterCheck(OK, f"{brand} — TSPL uyumlu.")
    if re.search(_GENERIC_LABEL, low):
        return PrinterCheck(
            UNKNOWN,
            "Termal etiket yazıcısı görünüyor. Çoğu TSPL destekler; "
            "“Test Baskı” ile doğrulayın.",
        )
    return PrinterCheck(
        UNKNOWN,
        "Model tanınmadı. Yazıcı TSPL / TSPL2 destekliyorsa çalışır; "
        "“Test Baskı” ile deneyin.",
    )


# Model adından çözünürlük tahmini (sürücü bildirmiyorsa)
_DPI_HINTS = (
    (r"600\s*dpi", 600),
    (r"300\s*dpi", 300),
    (r"203\s*dpi|200\s*dpi", 203),
    (r"\b(?:ttp|te|ta|da|me|mh|mx)[-_ ]?3\d\d", 300),  # TSC 3xx serisi
    (r"\b(?:ttp|te|ta|da|me|mh)[-_ ]?2\d\d", 203),      # TSC 2xx serisi
    (r"\bht3\d\d", 300),                                # HPRT HT300
    (r"xprinter|\bxp[-_ ]?\d", 203),
    (r"gprinter|\bgp[-_ ]?\d", 203),
)


def guess_dpi(name: str) -> int | None:
    low = (name or "").lower()
    for pattern, dpi in _DPI_HINTS:
        if re.search(pattern, low):
            return dpi
    return None


def pick_label_printer(printers: list[str]) -> str:
    """Kayıtlı yazıcı yoksa: listedeki ilk TSPL uyumlu görünen yazıcı."""
    for name in printers:
        if check_printer(name).status == OK:
            return name
    return ""
