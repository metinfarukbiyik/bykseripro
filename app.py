r"""
BYK Seri Baskı Pro — giriş noktası.

Kaynak kod src/ altındadır; bu dosya yalnızca onu yükleyip başlatır.

    python app.py              # Windows: scripts\windows\BASLAT.bat
                               # macOS  : scripts/macos/BASLAT.command
r"""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
if SRC.is_dir() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from main_window import main  # noqa: E402

if __name__ == "__main__":
    main()
