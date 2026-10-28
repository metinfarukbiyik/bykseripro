"""
Uygulama içi güncelleme — GitHub Releases (latest) üzerinden.

Akış:
  1) check_latest(): son sürümü sorgular, mevcut sürümden yeniyse bilgi döner
  2) install_update(): platform paketini indirir ve güncelleyiciyi başlatır
       Windows : Kurulum.exe --update  (uygulama kapanınca aynı klasöre kurar,
                 config.json / Excel korunur, sonra uygulamayı açar)
       macOS   : .app paketi kapanıştan sonra yerinde değiştirilir ve açılır
  3) Çağıran uygulamayı kapatır.

Kaynaktan çalışırken (python app.py) yalnız indirme sayfası açılır.
"""

from __future__ import annotations

import json
import os
import re
import ssl
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from branding import (
    APP_SHORT,
    GITHUB_REPO,
    SETUP_EXE_NAME,
    UPDATE_ASSET_MACOS,
    UPDATE_ASSET_WINDOWS,
)
from paths import is_frozen, is_macos, is_windows, resource_dir

API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases/latest"
DOWNLOAD_BASE = f"https://github.com/{GITHUB_REPO}/releases/latest/download"

ProgressFn = Callable[[int, int], None]  # (indirilen bayt, toplam bayt | 0)


@dataclass
class ReleaseInfo:
    version: str
    tag: str
    notes: str
    page_url: str
    asset_url: str  # bu platform için paket ("" → yalnız sayfa)


def current_version() -> str:
    for base in (resource_dir(), Path(__file__).resolve().parent):
        p = base / "VERSION"
        if p.is_file():
            ver = p.read_text(encoding="utf-8").strip()
            if ver:
                return ver
    return ""


def parse_version(raw: str) -> tuple[int, ...]:
    nums = re.findall(r"\d+", (raw or "").split("-", 1)[0])
    return tuple(int(n) for n in nums[:4]) or (0,)


def is_newer(candidate: str, current: str) -> bool:
    a, b = parse_version(candidate), parse_version(current)
    width = max(len(a), len(b))
    return a + (0,) * (width - len(a)) > b + (0,) * (width - len(b))


def _ssl_context() -> ssl.SSLContext:
    # Paketlenmiş Python'da sistem sertifikaları bulunamayabilir → certifi
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _open(url: str, timeout: float):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"{APP_SHORT}-updater",
            "Accept": "application/vnd.github+json",
        },
    )
    return urllib.request.urlopen(req, timeout=timeout, context=_ssl_context())


def _platform_asset() -> str:
    if is_windows():
        return UPDATE_ASSET_WINDOWS
    if is_macos():
        return UPDATE_ASSET_MACOS
    return ""


def fetch_latest(timeout: float = 8.0) -> ReleaseInfo:
    with _open(API_LATEST, timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    tag = str(data.get("tag_name") or "")
    version = tag.lstrip("vV") or str(data.get("name") or "")
    wanted = _platform_asset()
    asset_url = ""
    for asset in data.get("assets") or []:
        if asset.get("name") == wanted:
            asset_url = str(asset.get("browser_download_url") or "")
            break
    if wanted and not asset_url:
        asset_url = f"{DOWNLOAD_BASE}/{wanted}"
    return ReleaseInfo(
        version=version,
        tag=tag,
        notes=str(data.get("body") or "").strip(),
        page_url=str(data.get("html_url") or RELEASES_PAGE),
        asset_url=asset_url,
    )


def check_latest(timeout: float = 8.0) -> ReleaseInfo | None:
    """Daha yeni sürüm varsa bilgisini döner; yoksa None. Ağ hatası fırlatır."""
    current = current_version()
    info = fetch_latest(timeout)
    if current and info.version and is_newer(info.version, current):
        return info
    return None


# ── Kurulum ──────────────────────────────────────────────────────────


def _mac_bundle_path() -> Path | None:
    """Çalışan .app paketinin yolu (…/X.app/Contents/MacOS/exe)."""
    exe = Path(sys.executable).resolve()
    for parent in exe.parents:
        if parent.suffix == ".app":
            return parent
    return None


def self_update_blocker() -> str:
    """Yerinde güncelleme yapılamıyorsa nedeni (boş = yapılabilir)."""
    if not is_frozen():
        return "Kaynaktan çalışıyor; paket indirme sayfası açılacak."
    if is_windows():
        return ""
    if is_macos():
        bundle = _mac_bundle_path()
        if bundle is None:
            return ".app paketi bulunamadı."
        if "AppTranslocation" in str(bundle):
            return (
                "Uygulama İndirilenler’den geçici konumda çalışıyor. "
                "Uygulamayı Uygulamalar klasörüne taşıyıp yeniden açın."
            )
        if not os.access(bundle.parent, os.W_OK):
            return f"{bundle.parent} klasörüne yazma izni yok."
        return ""
    return "Bu platformda otomatik güncelleme yok."


def _download(url: str, dest: Path, progress: ProgressFn | None) -> None:
    with _open(url, timeout=30) as resp, open(dest, "wb") as out:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = resp.read(256 * 1024)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if progress:
                progress(done, total)
    if not zipfile.is_zipfile(dest):
        raise RuntimeError("İndirilen dosya geçerli bir paket değil.")


def install_update(info: ReleaseInfo, progress: ProgressFn | None = None) -> None:
    """
    Paketi indirir ve güncelleyiciyi arka planda başlatır.
    Döndükten sonra çağıran uygulamayı KAPATMALIDIR (güncelleyici onu bekler).
    """
    blocker = self_update_blocker()
    if blocker:
        raise RuntimeError(blocker)
    if not info.asset_url:
        raise RuntimeError("Bu platform için güncelleme paketi bulunamadı.")

    work = Path(tempfile.mkdtemp(prefix=f"{APP_SHORT}_update_"))
    archive = work / "update.zip"
    _download(info.asset_url, archive, progress)

    if is_windows():
        _launch_windows(work, archive)
    else:
        _launch_macos(work, archive)


def _launch_windows(work: Path, archive: Path) -> None:
    extract = work / "pkg"
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(extract)
    setups = list(extract.rglob(SETUP_EXE_NAME)) or list(extract.rglob("*Kurulum*.exe"))
    if not setups:
        raise RuntimeError(f"Pakette {SETUP_EXE_NAME} bulunamadı.")
    install_dir = Path(sys.executable).resolve().parent
    flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        [
            str(setups[0]),
            "--update",
            f"--dir={install_dir}",
            f"--wait-pid={os.getpid()}",
        ],
        cwd=str(setups[0].parent),
        creationflags=flags,
        close_fds=True,
    )


def _launch_macos(work: Path, archive: Path) -> None:
    bundle = _mac_bundle_path()
    assert bundle is not None
    extract = work / "pkg"
    extract.mkdir()
    # ditto: sembolik bağları ve çalıştırma izinlerini korur (zipfile korumaz)
    subprocess.run(["ditto", "-x", "-k", str(archive), str(extract)], check=True)
    apps = [p for p in extract.rglob("*.app") if p.name == bundle.name]
    if not apps:
        raise RuntimeError(f"Pakette {bundle.name} bulunamadı.")
    new_app = min(apps, key=lambda p: len(p.parts))

    script = work / "update.sh"
    script.write_text(
        f"""#!/bin/bash
while kill -0 {os.getpid()} 2>/dev/null; do sleep 0.5; done
TARGET={_sh(bundle)}
BACKUP={_sh(bundle.with_name(bundle.name + ".old"))}
rm -rf "$BACKUP"
if mv "$TARGET" "$BACKUP" && ditto {_sh(new_app)} "$TARGET"; then
  rm -rf "$BACKUP"
else
  rm -rf "$TARGET"; mv "$BACKUP" "$TARGET"
fi
xattr -dr com.apple.quarantine "$TARGET" 2>/dev/null
open "$TARGET"
rm -rf {_sh(work)}
""",
        encoding="utf-8",
    )
    subprocess.Popen(
        ["/bin/bash", str(script)],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _sh(path: Path) -> str:
    return "'" + str(path).replace("'", "'\\''") + "'"
