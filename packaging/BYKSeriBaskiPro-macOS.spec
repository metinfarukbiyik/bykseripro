# -*- mode: python ; coding: utf-8 -*-
# macOS .app — Yalnızca macOS'ta: scripts/macos/BUILD_APP.sh

# Spec packaging/ altında; yollar proje köküne göre, modüller src/ içinde
import os
import sys

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
SRC = os.path.join(ROOT, "src")
for _p in (SRC, SPECPATH):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def R(*parts):
    return os.path.join(ROOT, *parts)


from pathlib import Path

from PyInstaller.utils.hooks import collect_all

from branding import APP_BUNDLE_NAME, APP_DISPLAY, APP_SHORT, BUNDLE_ID

block_cipher = None

fa_datas, fa_binaries, fa_hiddenimports = collect_all("ctkfontawesome")

icon_path = R("assets", "app.icns") if Path(R("assets", "app.icns")).exists() else None
_ver = (Path(R("VERSION")).read_text(encoding="utf-8").strip() or "1.1.1")

a = Analysis(
    [R("app.py")],
    pathex=[SRC],
    binaries=fa_binaries,
    datas=[
        (R("assets"), "assets"),
        (R("resources", "config.json"), "."),
        (R("resources", "Barkod.xlsx"), "."),
        (R("VERSION"), "."),
        *fa_datas,
    ],
    hiddenimports=[
        "barcode",
        "barcode.codex",
        "barcode.writer",
        "openpyxl",
        "PIL",
        "PIL._tkinter_finder",
        "ctkfontawesome",
        "ui_icons",
        "qrcode",
        "qrcode.image.pil",
        "serial_dialog",
        "printer_raw",
        "branding",
        "certifi",
        "updater",
        "update_dialog",
        "layout_dialog",
        "text_render",
        "main_window",
        "label_entry_dialog",
        "printer_compat",
        *fa_hiddenimports,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["win32print", "win32api", "win32com", "pythoncom", "pywintypes"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_SHORT,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_SHORT,
)

app = BUNDLE(
    coll,
    name=APP_BUNDLE_NAME,
    icon=icon_path,
    bundle_identifier=BUNDLE_ID,
    info_plist={
        "CFBundleName": APP_DISPLAY,
        "CFBundleDisplayName": APP_DISPLAY,
        "CFBundleShortVersionString": _ver,
        "CFBundleVersion": _ver,
        "NSHighResolutionCapable": True,
        "NSHumanReadableCopyright": "© BIYIK.DEV",
        "CFBundleDocumentTypes": [],
    },
)
