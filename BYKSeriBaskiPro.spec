# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — BYK Seri Baskı Pro (Windows)

from PyInstaller.utils.hooks import collect_all

from branding import APP_SHORT
from win_version_info import APP_VERSION_INFO

block_cipher = None

fa_datas, fa_binaries, fa_hiddenimports = collect_all("ctkfontawesome")

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=fa_binaries,
    datas=[
        ("assets", "assets"),
        ("config.json", "."),
        ("Barkod.xlsx", "."),
        *fa_datas,
    ],
    hiddenimports=[
        "win32print",
        "win32api",
        "pywintypes",
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
        "branding",
        *fa_hiddenimports,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets\\app.ico",
    version=APP_VERSION_INFO,
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
