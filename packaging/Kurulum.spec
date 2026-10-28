# -*- mode: python ; coding: utf-8 -*-
# Tek dosya Kurulum.exe — gömülü payload.zip ile

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


from branding import SETUP_EXE_NAME
from win_version_info import SETUP_VERSION_INFO

block_cipher = None

# PyInstaller name = dosya adı uzantısız
_setup_name = SETUP_EXE_NAME.removesuffix(".exe")

a = Analysis(
    [R("src", "setup_wizard.py")],
    pathex=[SRC],
    binaries=[],
    datas=[
        (R("payload.zip"), "."),
        (R("VERSION"), "."),
        (R("assets", "app.ico"), "assets"),
        (R("assets", "app.png"), "assets"),
        (R("assets", "biyik_badge.png"), "assets"),
    ],
    hiddenimports=[
        "app_icon",
        "paths",
        "branding",
        "win32com",
        "win32com.client",
        "pythoncom",
        "pywintypes",
        "winreg",
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=_setup_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=R("assets", "app.ico"),
    version=SETUP_VERSION_INFO,
)
