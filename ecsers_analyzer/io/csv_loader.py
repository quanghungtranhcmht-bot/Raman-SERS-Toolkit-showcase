from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Any, Optional

from ecsers_analyzer.domain.spectrum import Spectrum
from ecsers_analyzer.io.metadata import parse_metadata_from_filename


def load_csv_spectrum(
    filepath: str | Path,
    laser_power_mw: float = 34.1,
    metadata_override: Optional[Dict[str, Any]] = None,
) -> Spectrum:
    """Load Raman CSV with two numeric columns (x, y), skipping non-numeric rows.

    Metadata is parsed from the filename using a strict-then-best-effort strategy.
    If metadata_override is provided (e.g., from a sidecar metadata.csv or user edits),
    non-None override values take precedence.
    """
    filepath = Path(filepath)

    x, y = [], []
    with filepath.open("r", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 2:
                continue
            try:
                x.append(float(row[0]))
                y.append(float(row[1]))
            except ValueError:
                continue

    md = parse_metadata_from_filename(str(filepath), best_effort=True)

    # Merge overrides (sidecar/user). Keep original parse fields for traceability.
    if metadata_override:
        md.setdefault("metadata_override", {})
        for k, v in metadata_override.items():
            if v is None:
                continue
            md["metadata_override"][k] = v
            md[k] = v
        md["metadata_source"] = "sidecar_or_user"
    else:
        md["metadata_source"] = md.get("parse_mode", "filename")

    md["laser_power_mw"] = float(laser_power_mw)

    return Spectrum(x=x, y=y, metadata=md)
