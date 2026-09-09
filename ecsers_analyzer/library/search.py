from __future__ import annotations

from pathlib import Path

import numpy as np

from ecsers_analyzer.library.spectral_library import list_references, load_reference_arrays, DEFAULT_LIBRARY_DIR


def _roi_mask(x, xlim):
    lo, hi = float(min(xlim)), float(max(xlim))
    return (x >= lo) & (x <= hi)


def _normalize_vector(y):
    y = np.asarray(y, dtype=float)
    y = y - np.nanmean(y)

    norm = np.linalg.norm(y)

    if not np.isfinite(norm) or norm <= 0:
        return y * 0

    return y / norm


def _resample_to_grid(x, y, grid):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    finite = np.isfinite(x) & np.isfinite(y)

    if not np.any(finite):
        return np.full_like(grid, np.nan, dtype=float)

    x = x[finite]
    y = y[finite]

    order = np.argsort(x)
    return np.interp(grid, x[order], y[order], left=np.nan, right=np.nan)


def cosine_similarity(y1, y2) -> float:
    y1 = _normalize_vector(y1)
    y2 = _normalize_vector(y2)

    finite = np.isfinite(y1) & np.isfinite(y2)

    if not np.any(finite):
        return float("nan")

    return float(np.dot(y1[finite], y2[finite]))


def pearson_similarity(y1, y2) -> float:
    y1 = np.asarray(y1, dtype=float)
    y2 = np.asarray(y2, dtype=float)

    finite = np.isfinite(y1) & np.isfinite(y2)

    if np.sum(finite) < 3:
        return float("nan")

    r = np.corrcoef(y1[finite], y2[finite])[0, 1]
    return float(r)


def search_library(
    query_spec,
    *,
    library_dir: Path = DEFAULT_LIBRARY_DIR,
    xlim=(400, 1700),
    grid_step=1.0,
    top_n=10,
):
    """
    Search processed query spectrum against the local SERS reference library.
    """
    refs = list_references(library_dir)

    if not refs:
        return []

    grid = np.arange(float(xlim[0]), float(xlim[1]) + float(grid_step), float(grid_step))

    qx = np.asarray(query_spec.x, dtype=float)
    qy = np.asarray(query_spec.y, dtype=float)

    q_grid = _resample_to_grid(qx, qy, grid)

    results = []

    for row in refs:
        try:
            arr = load_reference_arrays(row, library_dir)
            rx = arr["x"]
            ry = arr["y_processed"]

            r_grid = _resample_to_grid(rx, ry, grid)

            cos = cosine_similarity(q_grid, r_grid)
            pear = pearson_similarity(q_grid, r_grid)

            # Combined score. Cosine is primary; Pearson supports shape agreement.
            vals = [v for v in (cos, pear) if np.isfinite(v)]

            if vals:
                score = float(np.mean(vals))
            else:
                score = float("nan")

            results.append({
                "reference_id": row.get("reference_id", ""),
                "compound_name": row.get("compound_name", ""),
                "score": score,
                "cosine": cos,
                "pearson": pear,
                "metadata": row.get("metadata", {}),
                "notes": row.get("notes", ""),
            })

        except Exception:
            continue

    results = [r for r in results if np.isfinite(r["score"])]
    results.sort(key=lambda r: r["score"], reverse=True)

    return results[: int(top_n)]