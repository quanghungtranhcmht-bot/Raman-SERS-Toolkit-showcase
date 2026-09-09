from __future__ import annotations

import json
import uuid
from pathlib import Path
from datetime import datetime

import numpy as np

from ecsers_analyzer.persistence.app_paths import DEFAULT_LIBRARY_DIR

def _safe_name(text: str) -> str:
    out = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in str(text))
    out = out.strip("_")
    return out or "reference"


def _load_index(index_path: Path) -> list[dict]:
    if not index_path.exists():
        return []

    try:
        with index_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_index(index_path: Path, rows: list[dict]):
    index_path.parent.mkdir(parents=True, exist_ok=True)

    with index_path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, sort_keys=True)


def add_reference_spectrum(
    spec,
    *,
    compound_name: str,
    library_dir: Path = DEFAULT_LIBRARY_DIR,
    concentration_M=None,
    notes: str = "",
    known_peaks_cm1=None,
    quality_score=None,
):
    """
    Add the current processed spectrum to the local SERS reference library.
    """
    library_dir = Path(library_dir)
    spectra_dir = library_dir / "spectra"
    spectra_dir.mkdir(parents=True, exist_ok=True)

    ref_id = str(uuid.uuid4())[:12]
    compound_safe = _safe_name(compound_name)

    npz_name = f"{compound_safe}_{ref_id}.npz"
    npz_path = spectra_dir / npz_name

    x = np.asarray(spec.x, dtype=float)
    y_processed = np.asarray(spec.y, dtype=float)

    y_raw = np.asarray(getattr(spec, "y_raw", y_processed), dtype=float)
    x_raw = np.asarray(getattr(spec, "x_raw", x), dtype=float)

    baseline = getattr(spec, "baseline", None)

    if baseline is None:
        baseline = np.array([], dtype=float)
    else:
        baseline = np.asarray(baseline, dtype=float)

    np.savez_compressed(
        npz_path,
        x=x,
        y_processed=y_processed,
        x_raw=x_raw,
        y_raw=y_raw,
        baseline=baseline,
    )

    md = dict(getattr(spec, "metadata", {}) or {})

    recipe = getattr(spec, "processing_recipe", None)
    if recipe is None:
        recipe = getattr(spec, "processing_recipe_object", None)

    if hasattr(recipe, "to_dict"):
        recipe = recipe.to_dict()
    elif recipe is None:
        recipe = {}
    else:
        recipe = dict(recipe)

    row = {
        "reference_id": ref_id,
        "compound_name": str(compound_name),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "npz_file": str(npz_path.relative_to(library_dir)),
        "concentration_M": concentration_M,
        "known_peaks_cm1": list(known_peaks_cm1 or []),
        "quality_score": quality_score,
        "notes": str(notes or ""),
        "metadata": md,
        "processing_recipe": recipe,
    }

    index_path = library_dir / "references_index.json"
    rows = _load_index(index_path)
    rows.append(row)
    _save_index(index_path, rows)

    return row


def list_references(library_dir: Path = DEFAULT_LIBRARY_DIR) -> list[dict]:
    return _load_index(Path(library_dir) / "references_index.json")


def load_reference_arrays(row: dict, library_dir: Path = DEFAULT_LIBRARY_DIR):
    library_dir = Path(library_dir)
    npz_path = library_dir / row["npz_file"]

    data = np.load(npz_path)

    return {
        "x": data["x"],
        "y_processed": data["y_processed"],
        "x_raw": data["x_raw"],
        "y_raw": data["y_raw"],
        "baseline": data["baseline"],
    }