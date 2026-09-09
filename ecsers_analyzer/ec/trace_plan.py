from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import numpy as np


def trace_meta(trace: Any, key: str, default: Any = "") -> Any:
    """Read a value from trace.metadata first, then from trace attribute."""
    md = getattr(trace, "metadata", {}) or {}

    if key in md and md[key] not in (None, ""):
        return md[key]

    if hasattr(trace, key):
        value = getattr(trace, key)
        if value not in (None, ""):
            return value

    return default


def study_name(trace: Any) -> str:
    return str(trace_meta(trace, "study_name", "Unknown study"))


def trace_name(trace: Any) -> str:
    return str(
        getattr(trace, "name", "")
        or trace_meta(trace, "trace_name", "Unknown trace")
    )


def x_label(trace: Any) -> str:
    return str(
        getattr(trace, "xlabel", "")
        or trace_meta(trace, "x_label", "Time (s)")
    )


def y_label(trace: Any) -> str:
    return str(
        getattr(trace, "ylabel", "")
        or trace_meta(trace, "y_label", "Signal")
    )


def list_studies(traces: Sequence[Any]) -> list[str]:
    """Return sorted unique PAAX study names."""
    return sorted({study_name(trace) for trace in traces})


def traces_for_study(traces: Sequence[Any], selected_study: str) -> list[Any]:
    selected = str(selected_study or "").strip()

    if not selected:
        return []

    return [
        trace
        for trace in traces
        if study_name(trace) == selected
    ]


def trace_point_count(trace: Any) -> int:
    try:
        return len(trace.x)
    except Exception:
        return 0


def trace_dropdown_label(trace: Any, index: int) -> str:
    return (
        f"{index + 1:02d} | "
        f"{trace_name(trace)} | "
        f"{y_label(trace)} vs {x_label(trace)} | "
        f"n={trace_point_count(trace)}"
    )


def trace_dropdown_labels(traces: Sequence[Any]) -> list[str]:
    return [
        trace_dropdown_label(trace, i)
        for i, trace in enumerate(traces)
    ]


def selected_trace_from_visible(
    visible_traces: Sequence[Any],
    selected_index: int,
) -> Any | None:
    if not visible_traces:
        return None

    idx = int(selected_index)

    if idx < 0 or idx >= len(visible_traces):
        idx = 0

    return visible_traces[idx]


def trace_arrays(trace: Any) -> tuple[np.ndarray, np.ndarray]:
    """Return x/y arrays from a PAAX trace as float arrays."""
    x = np.asarray(getattr(trace, "x"), dtype=float)
    y = np.asarray(getattr(trace, "y"), dtype=float)
    return x, y


def trace_has_data(trace: Any) -> bool:
    try:
        x, y = trace_arrays(trace)
    except Exception:
        return False

    return x.size > 0 and y.size > 0


def trace_has_finite_data(trace: Any) -> bool:
    try:
        x, y = trace_arrays(trace)
    except Exception:
        return False

    return bool(np.isfinite(x).any() and np.isfinite(y).any())


def finite_trace_arrays(trace: Any) -> tuple[np.ndarray, np.ndarray]:
    """Return only paired finite x/y values.

    Used mainly for export/chart creation.
    """
    x, y = trace_arrays(trace)
    finite = np.isfinite(x) & np.isfinite(y)

    if not np.any(finite):
        return np.array([], dtype=float), np.array([], dtype=float)

    return x[finite], y[finite]


def paax_plot_trace_dict(
    trace: Any,
    *,
    source_path: str | Path | None = None,
    color_index: int = 0,
) -> dict:
    """Create the trace dictionary used by the shared trace table/plot helpers."""
    file_name = Path(source_path).name if source_path else ""

    return {
        "kind": "paax",
        "trace": trace,
        "label": trace_name(trace),
        "role": "ec trace",
        "file": file_name,
        "visible": True,
        "color_index": color_index,
    }


def paax_file_summary(path: str | Path | None, traces: Sequence[Any]) -> str:
    if path is None:
        return f"Loaded {len(traces)} trace(s)."

    return f"{Path(path).name}\nLoaded {len(traces)} trace(s)."


def paax_status_loaded(path: str | Path) -> str:
    return f"Loaded PAAX file: {Path(path).name}"


def paax_status_plotted(trace: Any) -> str:
    return f"Plotted EC trace: {study_name(trace)} — {trace_name(trace)}"


def paax_metadata_rows(
    trace: Any,
    *,
    source_path: str | Path | None = None,
    finite_only: bool = True,
) -> list[tuple[str, Any]]:
    """Build standard metadata rows for PAAX Excel export.

    This does not write Excel. It only centralizes the row planning.
    """
    if finite_only:
        x, y = finite_trace_arrays(trace)
    else:
        x, y = trace_arrays(trace)

    rows: list[tuple[str, Any]] = [
        ("source_file", Path(source_path).name if source_path else ""),
        ("study_name", study_name(trace)),
        ("trace_name", trace_name(trace)),
        ("x_label", x_label(trace)),
        ("y_label", y_label(trace)),
        ("n_points", len(x)),
    ]

    if len(x) and len(y):
        rows.extend(
            [
                ("x_min", float(np.nanmin(x))),
                ("x_max", float(np.nanmax(x))),
                ("y_min", float(np.nanmin(y))),
                ("y_max", float(np.nanmax(y))),
            ]
        )

    md = getattr(trace, "metadata", {}) or {}

    for key, value in sorted(md.items(), key=lambda kv: str(kv[0])):
        rows.append((str(key), str(value)))

    return rows