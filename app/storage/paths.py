from __future__ import annotations

import os
from pathlib import Path


def data_dir() -> Path:
    base = Path(os.getenv("JARVIS_DATA_DIR", "data")).expanduser()
    base.mkdir(parents=True, exist_ok=True)
    return base
