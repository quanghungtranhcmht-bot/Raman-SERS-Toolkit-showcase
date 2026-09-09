from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _env_path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    if value:
        return Path(value).expanduser().resolve()
    return default


DATA_DIR = _env_path("ECSERS_DATA_DIR", PROJECT_ROOT / "data")
DEFAULT_HISTORY_PATH = _env_path(
    "ECSERS_HISTORY_PATH",
    DATA_DIR / "user_history" / "processing_runs.jsonl",
)
DEFAULT_LIBRARY_DIR = _env_path(
    "ECSERS_LIBRARY_DIR",
    DATA_DIR / "spectral_library",
)
