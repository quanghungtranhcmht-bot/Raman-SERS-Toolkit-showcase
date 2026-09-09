from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime

from ecsers_analyzer.processing.analysis_features import extract_spectrum_features

from ecsers_analyzer.persistence.app_paths import DEFAULT_HISTORY_PATH


def _recipe_to_dict(recipe):
    if recipe is None:
        return {}

    if hasattr(recipe, "to_dict"):
        return recipe.to_dict()

    if isinstance(recipe, dict):
        return dict(recipe)

    return dict(getattr(recipe, "__dict__", {}) or {})


def append_jsonl(path: Path, record: dict):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


def load_history(path: Path = DEFAULT_HISTORY_PATH) -> list[dict]:
    path = Path(path)

    if not path.exists():
        return []

    records = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            try:
                records.append(json.loads(line))
            except Exception:
                continue

    return records


def log_processing_event(
    *,
    source_path=None,
    raw_spec=None,
    processed_spec=None,
    recipe=None,
    action: str = "processed",
    rating=None,
    notes: str = "",
    history_path: Path = DEFAULT_HISTORY_PATH,
):
    """
    Save one user behavior event.

    Good actions:
    - advisor_accepted
    - advisor_rejected
    - single_processed
    - batch_processed
    - library_search
    - export_single_excel
    - export_batch_excel
    - save_plot_png
    - add_to_library
    """
    md = {}

    if processed_spec is not None:
        md.update(dict(getattr(processed_spec, "metadata", {}) or {}))
    elif raw_spec is not None:
        md.update(dict(getattr(raw_spec, "metadata", {}) or {}))

    features = {}

    try:
        if raw_spec is not None:
            features = extract_spectrum_features(raw_spec)
        elif processed_spec is not None:
            features = extract_spectrum_features(processed_spec)
    except Exception:
        features = {}

    if recipe is None and processed_spec is not None:
        recipe = getattr(processed_spec, "processing_recipe_object", None)

    if recipe is None and processed_spec is not None:
        recipe = getattr(processed_spec, "processing_recipe", None)

    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "action": str(action),
        "source_path": str(source_path) if source_path is not None else "",
        "metadata": md,
        "features": features,
        "recipe": _recipe_to_dict(recipe),
        "processed_summary": {
            "n_spike_candidates": int(getattr(processed_spec, "n_spike_candidates", 0) or 0)
            if processed_spec is not None else 0,
            "n_spikes_removed": int(getattr(processed_spec, "n_spikes_removed", 0) or 0)
            if processed_spec is not None else 0,
            "normalization_method": str(getattr(processed_spec, "normalization_method", "") or "")
            if processed_spec is not None else "",
        },
        "user_feedback": {
            "rating": rating,
            "notes": str(notes or ""),
        },
    }

    append_jsonl(history_path, record)
    return record