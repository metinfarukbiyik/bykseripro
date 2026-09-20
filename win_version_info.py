"""Windows PE sürüm / yayıncı bilgisi (PyInstaller EXE version=...).

Dosya özellikleri → Ayrıntılar:
  Şirket adı / CompanyName = Biyik.dev

Not: SmartScreen “Bilinmeyen yayıncı” uyarısı Authenticode kod imzası ister;
bu kaynak yalnızca exe meta verisini doldurur.
"""

from __future__ import annotations

from pathlib import Path

from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)

from branding import (
    APP_DISPLAY,
    APP_SHORT,
    APP_TITLE,
    EXE_NAME,
    PUBLISHER,
    SETUP_EXE_NAME,
)

ROOT = Path(__file__).resolve().parent
COMPANY = PUBLISHER
COPYRIGHT = f"© {PUBLISHER}"
PRODUCT = APP_DISPLAY


def _version_tuple() -> tuple[int, int, int, int]:
    raw = (ROOT / "VERSION").read_text(encoding="utf-8").strip() or "1.0.0"
    parts: list[int] = []
    for piece in raw.split("."):
        try:
            parts.append(int("".join(ch for ch in piece if ch.isdigit()) or "0"))
        except ValueError:
            parts.append(0)
    while len(parts) < 4:
        parts.append(0)
    return parts[0], parts[1], parts[2], parts[3]


def make_version_info(
    *,
    file_description: str,
    internal_name: str,
    original_filename: str,
) -> VSVersionInfo:
    major, minor, patch, build = _version_tuple()
    ver_str = f"{major}.{minor}.{patch}.{build}"
    return VSVersionInfo(
        ffi=FixedFileInfo(
            filevers=(major, minor, patch, build),
            prodvers=(major, minor, patch, build),
            mask=0x3F,
            flags=0x0,
            OS=0x40004,  # VOS_NT_WINDOWS32
            fileType=0x1,  # VFT_APP
            subtype=0x0,
            date=(0, 0),
        ),
        kids=[
            StringFileInfo(
                [
                    StringTable(
                        "040904B0",
                        [
                            StringStruct("CompanyName", COMPANY),
                            StringStruct("FileDescription", file_description),
                            StringStruct("FileVersion", ver_str),
                            StringStruct("InternalName", internal_name),
                            StringStruct("LegalCopyright", COPYRIGHT),
                            StringStruct("OriginalFilename", original_filename),
                            StringStruct("ProductName", PRODUCT),
                            StringStruct("ProductVersion", ver_str),
                        ],
                    )
                ]
            ),
            VarFileInfo([VarStruct("Translation", [0x0409, 1200])]),
        ],
    )


APP_VERSION_INFO = make_version_info(
    file_description=APP_TITLE,
    internal_name=APP_SHORT,
    original_filename=EXE_NAME,
)

SETUP_VERSION_INFO = make_version_info(
    file_description=f"{APP_DISPLAY} — Kurulum ({PUBLISHER})",
    internal_name=SETUP_EXE_NAME.removesuffix(".exe"),
    original_filename=SETUP_EXE_NAME,
)
