r"""
BYK Seri Baskı Pro — giriş noktası.

Kaynak kod src/ altındadır; bu dosya yalnızca onu yükleyip başlatır.

    python app.py              # Windows: scripts\windows\BASLAT.bat
                               # macOS  : scripts/macos/BASLAT.command
"""

import os
import sys
from pathlib import Path


def _avoid_tk_console() -> None:
    """
    macOS: Finder/Dock'tan açılan uygulamanın stdin'i /dev/null'dur. Tk bunu görünce
    gizli bir "Tk konsol" penceresi ve menüsü kurar; macOS 27'de bu menü kurulumu
    (NSMenuItem başlığı boş) uygulamayı açılışta çökertir. stdin'i boş bir boruya
    bağlamak Tk'nın konsol yoluna hiç girmemesini sağlar (uygulama konsolu kullanmaz).
    Tk başlatılmadan önce çağrılmalıdır.
    """
    if sys.platform != "darwin":
        return
    os.environ.pop("TK_CONSOLE", None)
    try:
        if os.isatty(0):
            return
        read_end, write_end = os.pipe()
        os.dup2(read_end, 0)
        os.close(read_end)
        os.close(write_end)
    except OSError:
        pass


_avoid_tk_console()

SRC = Path(__file__).resolve().parent / "src"
if SRC.is_dir() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from main_window import main  # noqa: E402

if __name__ == "__main__":
    main()
