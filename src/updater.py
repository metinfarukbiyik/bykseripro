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
from paths import PROJECT_ROOT, is_frozen, is_macos, is_windows, resource_dir

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
    for base in (resource_dir(), PROJECT_ROOT):
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


def release_highlights(notes: str, limit: int = 12) -> list[str]:
    """
    Sürüm notundan kullanıcıya gösterilecek maddeler.
    Kaynak: GitHub Release metni (CI commit mesajlarından "## Yenilikler" üretir).
    Bu bölüm yoksa boş döner — indirme tabloları vb. kullanıcıya gösterilmez.
    """
    items: list[str] = []
    in_section = False
    for raw in (notes or "").splitlines():
        line = raw.strip()
        if line.startswith("#"):
            title = line.lstrip("#").strip().lower()
            in_section = "yenilik" in title or "neler yeni" in title
            continue
        if in_section and line[:2] in {"- ", "* "}:
            text = line[2:].strip().replace("**", "")
            if text:
                # Türkçe büyük harf: i → İ, ı → I
                first = {"i": "İ", "ı": "I"}.get(text[0], text[0].upper())
                items.append(first + text[1:])
    return items[:limit]


def _fetch_latest_via_redirect(timeout: float) -> ReleaseInfo:
    """
    API yanıt vermezse (saatlik 60 istek sınırı, ağ engeli): github.com/…/releases/latest
    adresi son sürümün etiket sayfasına yönlenir; sürüm adresten okunur. Sınırı yoktur.
    """
    req = urllib.request.Request(RELEASES_PAGE, headers={"User-Agent": f"{APP_SHORT}-updater"})
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
        final = resp.geturl()
    match = re.search(r"/releases/tag/([^/?#]+)", final)
    if not match:
        raise RuntimeError("Son sürüm bilgisi alınamadı.")
    tag = urllib.request.unquote(match.group(1))
    wanted = _platform_asset()
    return ReleaseInfo(
        version=tag.lstrip("vV"),
        tag=tag,
        notes="",
        page_url=final,
        asset_url=f"{DOWNLOAD_BASE}/{wanted}" if wanted else "",
    )


def fetch_latest(timeout: float = 8.0) -> ReleaseInfo:
    try:
        with _open(API_LATEST, timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return _fetch_latest_via_redirect(timeout)
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


def _mac_original_path(bundle: Path) -> Path | None:
    """
    macOS, internetten indirilip taşınmamış uygulamayı salt okunur geçici bir
    konumdan çalıştırır (App Translocation). Asıl konumu Security.framework verir.
    """
    if "AppTranslocation" not in str(bundle):
        return bundle
    try:
        import ctypes

        cf = ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
        )
        sec = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/Security.framework/Security")
        cf.CFURLCreateFromFileSystemRepresentation.restype = ctypes.c_void_p
        cf.CFURLCreateFromFileSystemRepresentation.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_bool,
        ]
        cf.CFURLGetFileSystemRepresentation.restype = ctypes.c_bool
        cf.CFURLGetFileSystemRepresentation.argtypes = [
            ctypes.c_void_p, ctypes.c_bool, ctypes.c_char_p, ctypes.c_long,
        ]
        cf.CFRelease.argtypes = [ctypes.c_void_p]
        sec.SecTranslocateCreateOriginalPathForURL.restype = ctypes.c_void_p
        sec.SecTranslocateCreateOriginalPathForURL.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

        raw = str(bundle).encode("utf-8")
        url = cf.CFURLCreateFromFileSystemRepresentation(None, raw, len(raw), True)
        if not url:
            return None
        original = sec.SecTranslocateCreateOriginalPathForURL(url, None)
        cf.CFRelease(url)
        if not original:
            return None
        buf = ctypes.create_string_buffer(4096)
        ok = cf.CFURLGetFileSystemRepresentation(original, True, buf, len(buf))
        cf.CFRelease(original)
        return Path(buf.value.decode("utf-8")) if ok and buf.value else None
    except Exception:
        return None


def mac_install_target() -> tuple[Path, bool] | None:
    """Güncellemenin kurulacağı .app yolu ve yönetici izni gerekip gerekmediği."""
    bundle = _mac_bundle_path()
    if bundle is None:
        return None
    target = _mac_original_path(bundle) or Path("/Applications") / bundle.name
    parent = target.parent
    writable = os.access(parent, os.W_OK) and (
        not target.exists() or os.access(target, os.W_OK)
    )
    return target, not writable


def self_update_blocker() -> str:
    """Yerinde güncelleme yapılamıyorsa nedeni (boş = yapılabilir)."""
    if not is_frozen():
        return "Kaynaktan çalışıyor; paket indirme sayfası açılacak."
    if is_windows():
        return ""
    if is_macos():
        # Geçici konum (App Translocation) ve yazma izni artık engel değil:
        # asıl konum bulunur, gerekirse yönetici parolası istenir
        return "" if _mac_bundle_path() is not None else ".app paketi bulunamadı."
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
    resolved = mac_install_target()
    assert resolved is not None
    target, needs_admin = resolved
    bundle = target
    extract = work / "pkg"
    extract.mkdir()
    # ditto: sembolik bağları ve çalıştırma izinlerini korur (zipfile korumaz)
    subprocess.run(["ditto", "-x", "-k", str(archive), str(extract)], check=True)
    apps = [p for p in extract.rglob("*.app") if p.name == bundle.name]
    if not apps:
        raise RuntimeError(f"Pakette {bundle.name} bulunamadı.")
    new_app = min(apps, key=lambda p: len(p.parts))

    log_dir = Path.home() / "Library" / "Logs" / APP_SHORT
    log_dir.mkdir(parents=True, exist_ok=True)
    log = log_dir / "update.log"

    # Değiştirme adımı (gerekirse yönetici yetkisiyle çalışır)
    replace = work / "replace.sh"
    replace.write_text(
        f"""#!/bin/bash
TARGET={_sh(target)}
BACKUP={_sh(target.with_name(target.name + ".old"))}
NEW={_sh(new_app)}
mkdir -p "$(dirname "$TARGET")"
rm -rf "$BACKUP"
if [ -d "$TARGET" ]; then mv "$TARGET" "$BACKUP" || exit 1; fi
if ditto "$NEW" "$TARGET"; then
  rm -rf "$BACKUP"
else
  rm -rf "$TARGET"
  [ -d "$BACKUP" ] && mv "$BACKUP" "$TARGET"
  exit 1
fi
# Karantina kalkar → bir dahaki açılışta geçici konuma (translocation) düşmez
xattr -dr com.apple.quarantine "$TARGET" 2>/dev/null
exit 0
""",
        encoding="utf-8",
    )
    if needs_admin:
        run_replace = (
            "osascript -e "
            + _sh_str(
                f'do shell script "/bin/bash " & quoted form of "{replace}" '
                f'with prompt "BYK Seri Baskı Pro güncellemesini kurmak için parolanızı girin." '
                "with administrator privileges"
            )
        )
    else:
        run_replace = f"/bin/bash {_sh(replace)}"

    script = work / "update.sh"
    script.write_text(
        f"""#!/bin/bash
exec >>{_sh(log)} 2>&1
echo "== $(date) güncelleme: {target} (yönetici: {'evet' if needs_admin else 'hayır'})"
while kill -0 {os.getpid()} 2>/dev/null; do sleep 0.5; done
if {run_replace}; then
  echo "kuruldu"
else
  echo "HATA: kurulamadı (kod $?)"
  osascript -e 'display alert "Güncelleme kurulamadı" message "Yeni sürümü biyik.dev/byk-seri-baski-pro sayfasından indirebilirsiniz. Ayrıntı: ~/Library/Logs/{APP_SHORT}/update.log"' >/dev/null 2>&1
fi
open {_sh(target)}
sleep 5
rm -rf {_sh(work)}
""",
        encoding="utf-8",
    )
    subprocess.Popen(
        ["/bin/bash", str(script)],
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _sh(path: Path) -> str:
    return _sh_str(str(path))


def _sh_str(text: str) -> str:
    """Kabuk için tek tırnaklı güvenli metin."""
    return "'" + text.replace("'", "'\\''") + "'"
