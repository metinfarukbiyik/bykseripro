"""Uygulama yolları — geliştirme, Windows exe ve macOS .app uyumlu."""

from __future__ import annotations

import platform
import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def is_macos() -> bool:
    return platform.system() == "Darwin"


def is_windows() -> bool:
    return platform.system() == "Windows"


def resource_dir() -> Path:
    """Salt okunur kaynaklar (assets). Exe/.app içinde _MEIPASS veya Resources."""
    if is_frozen() and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)

    if is_frozen() and is_macos():
        # .app/Contents/MacOS/exe → Contents/Resources
        exe = Path(sys.executable).resolve()
        resources = exe.parent.parent / "Resources"
        if resources.is_dir():
            return resources

    return Path(__file__).resolve().parent


def app_home() -> Path:
    """Yazılabilir dizin: config, excel varsayılanı."""
    if is_frozen():
        if is_macos():
            # .app salt okunur olabilir → Application Support
            from branding import APP_SHORT, SUPPORT_VENDOR

            home = (
                Path.home()
                / "Library"
                / "Application Support"
                / SUPPORT_VENDOR
                / APP_SHORT
            )
            home.mkdir(parents=True, exist_ok=True)
            return home
        if is_windows():
            return Path(sys.executable).resolve().parent
        # Linux AppImage / frozen
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


def assets_dir() -> Path:
    base = resource_dir()
    assets = base / "assets"
    if assets.is_dir():
        return assets
    # macOS: bazen assets doğrudan Resources altında
    return base
