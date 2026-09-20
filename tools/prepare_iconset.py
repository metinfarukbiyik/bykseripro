"""Geriye uyumluluk: tools/prepare_icons.py çağırır."""

from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("prepare_icons.py")), run_name="__main__")
