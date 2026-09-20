"""
BYK Seri Baskı Pro — Tek tık Kurulum sihirbazı (Biyik.dev)

Alıcıda Python gerekmez. Kurulum.exe çift tıklanınca:
  - Kullanıcı kurulum klasörünü seçer (AppData veya Program Files vb.)
  - Başlat menüsü + masaüstü kısayolu oluşturur
  - Denetim Masası / Uygulamalar listesine kaldırma kaydı ekler
  - İsteğe bağlı olarak uygulamayı başlatır
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import threading
import zipfile
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from branding import (
    APP_DISPLAY,
    APP_REG_ID,
    APP_SHORT,
    EXE_NAME,
    PUBLISHER,
    PUBLISHER_FOLDER,
    SHORTCUT_NAME,
    SUPPORT_VENDOR,
)

APP_NAME = APP_DISPLAY
START_MENU_FOLDER = PUBLISHER_FOLDER
UNINSTALL_SUBKEY = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_REG_ID}"

C_BG = "#F3F5F7"
C_CARD = "#FFFFFF"
C_NAVY = "#1B3352"
C_GOLD = "#B8962E"
C_MUTED = "#6B7380"
C_LINE = "#E6E9EE"
C_OK = "#2E7D4F"


def _version() -> str:
    for base in (_bundle_dir(), Path(__file__).resolve().parent):
        p = base / "VERSION"
        if p.exists():
            return p.read_text(encoding="utf-8").strip() or "1.1.1"
    return "1.1.1"


def _bundle_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def _default_user_root() -> Path:
    local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(local) / SUPPORT_VENDOR / APP_SHORT


def _default_program_files_root() -> Path:
    pf = os.environ.get("ProgramFiles") or r"C:\Program Files"
    return Path(pf) / PUBLISHER_FOLDER / APP_SHORT


def _install_root() -> Path:
    """Geriye uyumluluk / varsayılan."""
    return _default_user_root()


def _is_admin() -> bool:
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _path_needs_admin(dest: Path) -> bool:
    """Program Files / Windows gibi korumalı konumlar."""
    try:
        resolved = str(dest.resolve()).lower()
    except OSError:
        resolved = str(dest).lower()
    protected = []
    for key in ("ProgramFiles", "ProgramFiles(x86)", "SystemRoot"):
        val = os.environ.get(key)
        if val:
            protected.append(str(Path(val).resolve()).lower())
    return any(resolved == p or resolved.startswith(p + os.sep) for p in protected)


def _relaunch_elevated(args: list[str]) -> bool:
    """Yönetici olarak yeniden başlat. Başarılıysa True."""
    try:
        import ctypes

        if getattr(sys, "frozen", False):
            exe = str(Path(sys.executable).resolve())
            params = subprocess_list_to_cmdline(args)
        else:
            exe = sys.executable
            script = str(Path(__file__).resolve())
            params = subprocess_list_to_cmdline([script, *args])

        rc = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", exe, params, None, 1
        )
        return rc > 32
    except Exception:
        return False


def subprocess_list_to_cmdline(args: list[str]) -> str:
    parts: list[str] = []
    for a in args:
        if not a:
            parts.append('""')
        elif any(ch in a for ch in ' \t"'):
            parts.append('"' + a.replace('"', '\\"') + '"')
        else:
            parts.append(a)
    return " ".join(parts)


def _find_payload_zip() -> Path | None:
    """Önce gömülü payload, sonra yan klasör/zip."""
    bundled = _bundle_dir() / "payload.zip"
    if bundled.exists():
        return bundled
    here = (
        Path(sys.executable).resolve().parent
        if getattr(sys, "frozen", False)
        else Path(__file__).resolve().parent
    )
    for candidate in (
        here / "payload.zip",
        here / f"{APP_SHORT}.zip",
        here.parent / "dist" / "payload.zip",
    ):
        if candidate.exists():
            return candidate
    return None


def _find_app_folder() -> Path | None:
    """Geliştirme / taşınabilir paket: hazır klasör."""
    here = (
        Path(sys.executable).resolve().parent
        if getattr(sys, "frozen", False)
        else Path(__file__).resolve().parent
    )
    for candidate in (
        here / APP_SHORT,
        here / "app",
        here.parent / "dist" / APP_SHORT,
    ):
        if (candidate / EXE_NAME).exists():
            return candidate
    return None


def _icon_location(icon: Path) -> str:
    """ICO dosyası ise indeks yok; exe ise ,0."""
    if icon.suffix.lower() == ".ico":
        return str(icon)
    return f"{icon},0"


def _create_shortcut(path: Path, target: Path, workdir: Path, icon: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    icon_loc = _icon_location(icon)
    try:
        import win32com.client  # type: ignore

        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(path))
        shortcut.Targetpath = str(target)
        shortcut.WorkingDirectory = str(workdir)
        shortcut.IconLocation = icon_loc
        shortcut.Description = f"{APP_NAME} - {PUBLISHER}"
        shortcut.save()
        return
    except Exception:
        pass

    ps1 = Path(tempfile.gettempdir()) / f"biyik_shortcut_{os.getpid()}.ps1"
    content = f"""
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut(@'
{path}
'@)
$s.TargetPath = @'
{target}
'@
$s.WorkingDirectory = @'
{workdir}
'@
$s.IconLocation = @'
{icon_loc}
'@
$s.Description = @'
{APP_NAME} - {PUBLISHER}
'@
$s.Save()
"""
    ps1.write_text(content, encoding="utf-8")
    try:
        os.system(
            f'powershell -NoProfile -ExecutionPolicy Bypass -File "{ps1}" >nul 2>&1'
        )
    finally:
        try:
            ps1.unlink(missing_ok=True)
        except OSError:
            pass


def _desktop_dir() -> Path:
    """OneDrive yönlendirmeli masaüstü dahil gerçek Desktop klasörü."""
    try:
        import win32com.client  # type: ignore

        shell = win32com.client.Dispatch("WScript.Shell")
        desk = shell.SpecialFolders("Desktop")
        if desk:
            return Path(desk)
    except Exception:
        pass
    try:
        import subprocess

        out = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "[Environment]::GetFolderPath('Desktop')",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if out:
            return Path(out)
    except Exception:
        pass
    return Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"


def _resolve_shortcut_icon(dest: Path, exe: Path) -> Path:
    """Kısayol için app.ico tercih et; yoksa exe gömülü ikon."""
    candidates = (
        dest / "app.ico",
        dest / "_internal" / "assets" / "app.ico",
        dest / "assets" / "app.ico",
    )
    for c in candidates:
        if c.is_file():
            return c
    return exe


def _start_menu_dir() -> Path:
    appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / START_MENU_FOLDER


def _dir_size_kb(root: Path) -> int:
    total = 0
    try:
        for f in root.rglob("*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return max(1, total // 1024)


def _register_add_remove_programs(dest: Path) -> str:
    """Denetim Masası / Ayarlar → Uygulamalar kaydı. Dönüş: HKCU|HKLM."""
    import winreg

    exe = dest / EXE_NAME
    uninst = dest / "KALDIR.bat"
    icon = dest / "app.ico"
    display_icon = str(icon) if icon.is_file() else f"{exe},0"
    size_kb = _dir_size_kb(dest)

    use_hklm = _path_needs_admin(dest) and _is_admin()
    hive = winreg.HKEY_LOCAL_MACHINE if use_hklm else winreg.HKEY_CURRENT_USER
    hive_name = "HKLM" if use_hklm else "HKCU"

    key = winreg.CreateKeyEx(hive, UNINSTALL_SUBKEY, 0, winreg.KEY_WRITE)
    try:
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, _version())
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, PUBLISHER)
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(dest))
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, display_icon)
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{uninst}"')
        winreg.SetValueEx(
            key,
            "QuietUninstallString",
            0,
            winreg.REG_SZ,
            f'"{uninst}" /S',
        )
        winreg.SetValueEx(key, "InstallSource", 0, winreg.REG_SZ, PUBLISHER)
        winreg.SetValueEx(key, "URLInfoAbout", 0, winreg.REG_SZ, "https://biyik.dev")
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, int(size_kb))
    finally:
        winreg.CloseKey(key)

    (dest / "uninstall.hive").write_text(hive_name, encoding="utf-8")
    return hive_name


def _write_uninstaller(dest: Path) -> None:
    bat = dest / "KALDIR.bat"
    bat.write_text(
        f"""@echo off
chcp 65001 >nul
setlocal EnableExtensions
set "DEST={dest}"
set "MENU=%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\{START_MENU_FOLDER}"
for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"`) do set "DESKDIR=%%D"
if not defined DESKDIR set "DESKDIR=%USERPROFILE%\\Desktop"
set "DESK=%DESKDIR%\\{SHORTCUT_NAME}"
set "SILENT=0"
if /i "%~1"=="/S" set "SILENT=1"
if /i "%~1"=="/silent" set "SILENT=1"

if "%SILENT%"=="0" echo {APP_NAME} kaldiriliyor...
taskkill /IM {EXE_NAME} /F >nul 2>&1

REM Denetim Masasi / Uygulamalar kaydi
reg delete "HKCU\\{UNINSTALL_SUBKEY}" /f >nul 2>&1
reg delete "HKLM\\{UNINSTALL_SUBKEY}" /f >nul 2>&1

if exist "%MENU%\\{SHORTCUT_NAME}" del /f /q "%MENU%\\{SHORTCUT_NAME}"
if exist "%DESK%" del /f /q "%DESK%"
if exist "%MENU%" rd "%MENU%" 2>nul

cd /d "%TEMP%"
if exist "%DEST%" rd /s /q "%DEST%"

if "%SILENT%"=="0" (
  echo Kaldirma tamamlandi.
  pause
)
endlocal
""",
        encoding="utf-8",
    )


def _ensure_writable(dest: Path) -> None:
    """Klasöre yazılabildiğini doğrula; değilse PermissionError."""
    dest.mkdir(parents=True, exist_ok=True)
    probe = dest / ".biyik_write_test"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        raise PermissionError(
            f"Bu klasöre yazılamıyor:\n{dest}\n\n"
            "Program Files gibi korumalı bir konum seçtiyseniz "
            "kurulumu yönetici olarak çalıştırın."
        ) from exc


def install_files(progress_cb=None, dest: Path | None = None) -> Path:
    dest = Path(dest) if dest is not None else _default_user_root()
    dest = dest.expanduser()

    if progress_cb:
        progress_cb(5, "Kurulum klasörü hazırlanıyor…")

    if _path_needs_admin(dest) and not _is_admin():
        raise PermissionError(
            "Seçilen konum yönetici izni gerektiriyor.\n"
            f"{dest}\n\n"
            "Kurulumu yönetici olarak yeniden başlatın veya "
            "kullanıcı klasörüne (AppData) kurun."
        )

    zip_path = _find_payload_zip()
    folder = _find_app_folder()

    if dest.exists():
        try:
            shutil.rmtree(dest)
        except OSError:
            pass

    _ensure_writable(dest)

    if zip_path is not None:
        if progress_cb:
            progress_cb(20, "Paket açılıyor…")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmp_path)
            extracted = tmp_path
            if not (extracted / EXE_NAME).exists():
                subs = [p for p in extracted.iterdir() if p.is_dir()]
                for sub in subs:
                    if (sub / EXE_NAME).exists():
                        extracted = sub
                        break
            if not (extracted / EXE_NAME).exists():
                raise FileNotFoundError("Kurulum paketinde uygulama exe bulunamadı.")
            if progress_cb:
                progress_cb(55, "Dosyalar kopyalanıyor…")
            for item in extracted.iterdir():
                target = dest / item.name
                if item.is_dir():
                    shutil.copytree(item, target, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, target)
    elif folder is not None:
        if progress_cb:
            progress_cb(30, "Dosyalar kopyalanıyor…")
        shutil.copytree(folder, dest, dirs_exist_ok=True)
    else:
        raise FileNotFoundError(
            "Kurulum verisi bulunamadı.\n"
            f"payload.zip veya {APP_SHORT} klasörü eksik.\n"
            "Lütfen BUILD_RELEASE.bat ile üretilmiş Kurulum.exe kullanın."
        )

    if not (dest / EXE_NAME).exists():
        raise FileNotFoundError(f"Kurulum sonrası {EXE_NAME} bulunamadı.")

    if progress_cb:
        progress_cb(75, "Kısayollar oluşturuluyor…")

    exe = dest / EXE_NAME
    for src_ico in (
        dest / "_internal" / "assets" / "app.ico",
        dest / "assets" / "app.ico",
        _bundle_dir() / "assets" / "app.ico",
    ):
        if src_ico.is_file():
            try:
                shutil.copy2(src_ico, dest / "app.ico")
            except OSError:
                pass
            break

    icon = _resolve_shortcut_icon(dest, exe)
    menu = _start_menu_dir()
    menu.mkdir(parents=True, exist_ok=True)
    _create_shortcut(menu / SHORTCUT_NAME, exe, dest, icon)
    _create_shortcut(_desktop_dir() / SHORTCUT_NAME, exe, dest, icon)
    _write_uninstaller(dest)

    if progress_cb:
        progress_cb(90, "Denetim Masası kaydı ekleniyor…")
    try:
        _register_add_remove_programs(dest)
    except OSError as exc:
        # Kısmi başarı: uygulama kuruldu, liste kaydı başarısız olabilir
        print(f"Uninstall registry uyarısı: {exc}", file=sys.stderr)

    (dest / "VERSION.txt").write_text(
        f"{APP_NAME}\n{PUBLISHER}\nSürüm: {_version()}\nKurulum: {dest}\n",
        encoding="utf-8",
    )

    if progress_cb:
        progress_cb(100, "Kurulum tamamlandı.")
    return dest


def _parse_dir_arg(argv: list[str]) -> Path | None:
    for i, a in enumerate(argv):
        if a.startswith("/DIR="):
            return Path(a[5:].strip().strip('"'))
        if a.startswith("--dir="):
            return Path(a[6:].strip().strip('"'))
        if a in {"/DIR", "--dir"} and i + 1 < len(argv):
            return Path(argv[i + 1].strip().strip('"'))
    return None


class SetupApp(tk.Tk):
    def __init__(self, initial_dir: Path | None = None) -> None:
        super().__init__()
        self.title(f"{APP_NAME} — Kurulum")
        self.configure(bg=C_BG)
        self.resizable(False, False)
        self.geometry("560x520")
        self._center()
        try:
            from app_icon import apply_app_icon

            apply_app_icon(self)
        except Exception:
            pass

        self.progress_var = tk.DoubleVar(value=0)
        self.status_var = tk.StringVar(value="Kuruluma hazır. Klasörü seçebilirsiniz.")
        self.dest_var = tk.StringVar(
            value=str(initial_dir or _default_user_root())
        )
        self.launch_var = tk.BooleanVar(value=True)
        self._busy = False

        card = tk.Frame(
            self, bg=C_CARD, highlightbackground=C_LINE, highlightthickness=1
        )
        card.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(
            card,
            text=PUBLISHER,
            font=("Segoe UI Semibold", 11),
            fg=C_GOLD,
            bg=C_CARD,
        ).pack(anchor="w", padx=20, pady=(18, 0))
        tk.Label(
            card,
            text=APP_NAME,
            font=("Segoe UI Semibold", 14),
            fg=C_NAVY,
            bg=C_CARD,
        ).pack(anchor="w", padx=20, pady=(2, 0))
        tk.Label(
            card,
            text=f"Sürüm {_version()}  ·  Windows kurulum sihirbazı",
            font=("Segoe UI", 9),
            fg=C_MUTED,
            bg=C_CARD,
        ).pack(anchor="w", padx=20, pady=(4, 12))

        tk.Frame(card, bg=C_LINE, height=1).pack(fill="x", padx=20)

        tk.Label(
            card,
            text=(
                "Kurulum klasörünü seçin. AppData yönetici istemez;\n"
                "Program Files için yönetici onayı gerekir.\n"
                "Kaldırma: Windows Ayarlar → Uygulamalar veya Denetim Masası."
            ),
            font=("Segoe UI", 9),
            fg=C_NAVY,
            bg=C_CARD,
            justify="left",
        ).pack(anchor="w", padx=20, pady=12)

        tk.Label(
            card, text="Kurulum klasörü:", font=("Segoe UI", 8), fg=C_MUTED, bg=C_CARD
        ).pack(anchor="w", padx=20)

        path_row = tk.Frame(card, bg=C_CARD)
        path_row.pack(fill="x", padx=20, pady=(4, 4))
        self.path_entry = ttk.Entry(path_row, textvariable=self.dest_var)
        self.path_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(path_row, text="Gözat…", width=10, command=self._browse).pack(
            side="left", padx=(8, 0)
        )

        presets = tk.Frame(card, bg=C_CARD)
        presets.pack(fill="x", padx=20, pady=(0, 8))
        ttk.Button(
            presets,
            text="Kullanıcı klasörü (önerilen)",
            command=lambda: self.dest_var.set(str(_default_user_root())),
        ).pack(side="left")
        ttk.Button(
            presets,
            text="Program Files",
            command=lambda: self.dest_var.set(str(_default_program_files_root())),
        ).pack(side="left", padx=(8, 0))

        ttk.Checkbutton(
            card,
            text="Kurulumdan sonra uygulamayı başlat",
            variable=self.launch_var,
        ).pack(anchor="w", padx=20)

        self.bar = ttk.Progressbar(
            card, variable=self.progress_var, maximum=100, length=480
        )
        self.bar.pack(padx=20, pady=(16, 6))
        tk.Label(
            card,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
            fg=C_MUTED,
            bg=C_CARD,
        ).pack(anchor="w", padx=20)

        actions = tk.Frame(card, bg=C_CARD)
        actions.pack(fill="x", padx=20, pady=16)
        self.btn_close = ttk.Button(actions, text="Kapat", command=self.destroy)
        self.btn_close.pack(side="right")
        self.btn_install = ttk.Button(
            actions, text="Kurulumu Başlat", command=self._start
        )
        self.btn_install.pack(side="right", padx=(0, 8))

    def _center(self) -> None:
        self.update_idletasks()
        w, h = 560, 520
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _browse(self) -> None:
        current = Path(self.dest_var.get().strip() or _default_user_root())
        initial = current if current.is_dir() else current.parent
        if not initial.exists():
            initial = Path.home()
        chosen = filedialog.askdirectory(
            parent=self,
            title="Kurulum klasörünü seçin",
            initialdir=str(initial),
        )
        if not chosen:
            return
        path = Path(chosen)
        # Kullanıcı üst klasör seçtiyse uygulama alt klasörünü ekle
        if path.name.lower() != APP_SHORT.lower():
            path = path / APP_SHORT
        self.dest_var.set(str(path))

    def _set_progress(self, value: float, text: str) -> None:
        self.progress_var.set(value)
        self.status_var.set(text)
        self.update_idletasks()

    def _start(self) -> None:
        if self._busy:
            return
        raw = (self.dest_var.get() or "").strip()
        if not raw:
            messagebox.showerror("Kurulum", "Kurulum klasörü boş olamaz.")
            return
        dest = Path(raw)

        if _path_needs_admin(dest) and not _is_admin():
            ok = messagebox.askyesno(
                "Yönetici izni",
                "Program Files (veya korumalı bir klasör) seçildi.\n"
                "Kuruluma devam etmek için yönetici onayı gerekir.\n\n"
                "Yönetici olarak yeniden başlatılsın mı?",
                parent=self,
            )
            if not ok:
                return
            if _relaunch_elevated([f"/DIR={dest}", "/INSTALL"]):
                self.destroy()
                return
            messagebox.showerror(
                "Kurulum",
                "Yönetici olarak yeniden başlatılamadı.\n"
                "Kurulum.exe’ye sağ tıklayıp “Yönetici olarak çalıştır” deneyin.",
                parent=self,
            )
            return

        self._busy = True
        self.btn_install.configure(state="disabled")
        self.btn_close.configure(state="disabled")
        self.path_entry.configure(state="disabled")

        def work() -> None:
            try:

                def cb(v, t):
                    self.after(0, lambda: self._set_progress(v, t))

                result = install_files(cb, dest=dest)
                self.after(0, lambda: self._done(result, None))
            except Exception as exc:
                self.after(0, lambda: self._done(None, exc))

        threading.Thread(target=work, daemon=True).start()

    def _done(self, dest: Path | None, err: Exception | None) -> None:
        self._busy = False
        self.btn_close.configure(state="normal")
        self.path_entry.configure(state="normal")
        if err is not None:
            self.btn_install.configure(state="normal")
            self.status_var.set("Kurulum başarısız.")
            messagebox.showerror("Kurulum", str(err))
            return
        self.status_var.set("Kurulum tamamlandı.")
        self.progress_var.set(100)
        messagebox.showinfo(
            "Kurulum",
            f"{APP_NAME} kuruldu.\n\n"
            f"Klasör:\n{dest}\n\n"
            "Başlat menüsü ve masaüstünde kısayol oluşturuldu.\n"
            "Kaldırmak için: Windows Ayarlar → Uygulamalar\n"
            "veya Denetim Masası → Program ekle/kaldır\n"
            f"(Yayıncı: {PUBLISHER})",
        )
        if self.launch_var.get() and dest is not None:
            try:
                os.startfile(str(dest / EXE_NAME))  # type: ignore[attr-defined]
            except Exception:
                pass
        self.destroy()


def main() -> None:
    argv = sys.argv[1:]
    dir_arg = _parse_dir_arg(argv)
    silent = any(a in {"/S", "/silent", "--silent"} for a in argv)
    auto_install = any(a in {"/INSTALL", "--install"} for a in argv)

    if silent or (auto_install and dir_arg is not None and _is_admin()):
        dest = dir_arg or _default_user_root()
        try:
            if _path_needs_admin(dest) and not _is_admin():
                if _relaunch_elevated(
                    [f"/DIR={dest}", "/S" if silent else "/INSTALL"]
                ):
                    return
                raise PermissionError("Yönetici izni gerekli.")
            result = install_files(dest=dest)
            if silent:
                print(f"OK {result}")
            else:
                # Yükseltilmiş otomatik kurulum — kısa bilgilendirme
                root = tk.Tk()
                root.withdraw()
                messagebox.showinfo(
                    "Kurulum",
                    f"{APP_NAME} kuruldu.\n\n{result}\n\n"
                    "Kaldırma: Ayarlar → Uygulamalar",
                )
                if not any(a in {"/NOLAUNCH", "--no-launch"} for a in argv):
                    try:
                        os.startfile(str(result / EXE_NAME))  # type: ignore[attr-defined]
                    except Exception:
                        pass
                root.destroy()
        except Exception as exc:
            if silent:
                print(f"ERR {exc}", file=sys.stderr)
                sys.exit(1)
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Kurulum", str(exc))
            root.destroy()
            sys.exit(1)
        return

    app = SetupApp(initial_dir=dir_arg)
    app.mainloop()


if __name__ == "__main__":
    main()
