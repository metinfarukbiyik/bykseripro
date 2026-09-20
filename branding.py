"""Ürün kimliği — tek kaynak (görünen ad, exe, .app, yollar)."""

from __future__ import annotations

# Görünen adlar
APP_DISPLAY = "BYK Seri Baskı Pro"
APP_TITLE = "BYK Seri Baskı Pro — Biyik.dev"
APP_SHORT = "BYKSeriBaskiPro"  # klasör / exe kök adı / .app CFBundleExecutable

PUBLISHER = "Biyik.dev"
PUBLISHER_FOLDER = "Biyik.dev"  # Start Menu
SUPPORT_VENDOR = "BiyikDev"  # Application Support / LocalAppData

EXE_NAME = f"{APP_SHORT}.exe"
SETUP_EXE_NAME = f"{APP_SHORT}_Kurulum.exe"
APP_BUNDLE_NAME = f"{APP_SHORT}.app"
SHORTCUT_NAME = f"{APP_DISPLAY}.lnk"
DESKTOP_ALIAS = APP_DISPLAY

BUNDLE_ID = "dev.biyik.seribaskipro"
APP_REG_ID = f"BiyikDev_{APP_SHORT}"

# PyInstaller / release çıktı adları
SPEC_WIN = f"{APP_SHORT}.spec"
SPEC_MAC = f"{APP_SHORT}-macOS.spec"
RELEASE_PREFIX = APP_SHORT
