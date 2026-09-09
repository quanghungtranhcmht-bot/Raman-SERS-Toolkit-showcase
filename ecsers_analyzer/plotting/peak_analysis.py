from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from ecsers_analyzer.plotting.trace_builder import trace_xy


def safe_peak_window_cm1(text: str, default: float = 5.0) -> float:
    """Parse peak-search half-window in cm⁻¹."""
    try:
        value = abs(float(text))
    except Exception:
        value = float(default)

    if value <= 0:
        value = float(default)

    return value


def nearest_y_for_trace(trace: dict, x0: float) -> float:
    """Return nearest non-offset intensity for one trace at x0."""
    x, y = trace_xy(trace)

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    if x.size == 0 or y.size == 0:
        return float("nan")

    finite = np.isfinite(x) & np.isfinite(y)

    if not np.any(finite):
        return float("nan")

    x = x[finite]
    y = y[finite]

    idx = int(np.argmin(np.abs(x - float(x0))))
    return float(y[idx])


def peak_value_for_trace(
    trace: dict,
    x0: float,
    *,
    method: str = "nearest",
    half_window_cm1: float = 5.0,
) -> float:
    """Return peak intensity for one trace at marker position."""
    method = str(method or "nearest").lower()

    x, y = trace_xy(trace)

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    finite = np.isfinite(x) & np.isfinite(y)

    if not np.any(finite):
        return float("nan")

    x = x[finite]
    y = y[finite]

    if method == "local_max_window":
        half_window = safe_peak_window_cm1(str(half_window_cm1))
        mask = np.abs(x - float(x0)) <= half_window

        if np.any(mask):
            return float(np.nanmax(y[mask]))

    idx = int(np.argmin(np.abs(x - float(x0))))
    return float(y[idx])


def _marker_value(marker: Any, key: str, default: Any = None) -> Any:
    if isinstance(marker, dict):
        return marker.get(key, default)
    return getattr(marker, key, default)


def peak_intensity_matrix(
    *,
    traces: Sequence[dict],
    markers: Sequence[Any],
    method: str = "nearest",
    half_window_cm1: float = 5.0,
) -> tuple[list[str], list[list[Any]]]:
    """Build headers and rows for the peak intensity analysis table."""
    visible_traces = [tr for tr in traces if tr.get("visible", True)]
    visible_markers = [
        m for m in markers
        if bool(_marker_value(m, "visible", True))
    ]

    headers = ["Trace", "Role", "File"]

    for marker in visible_markers:
        label = str(_marker_value(marker, "label", "") or "").strip()
        x = float(_marker_value(marker, "x", float("nan")))

        if not label:
            label = f"{x:.2f} cm⁻¹"

        headers.append(label)

    rows: list[list[Any]] = []

    for trace in visible_traces:
        row: list[Any] = [
            str(trace.get("label", "")),
            str(trace.get("role", "")),
            str(trace.get("file", "")),
        ]

        for marker in visible_markers:
            x = float(_marker_value(marker, "x", float("nan")))

            value = peak_value_for_trace(
                trace,
                x,
                method=method,
                half_window_cm1=half_window_cm1,
            )

            if np.isfinite(value):
                row.append(float(value))
            else:
                row.append("")

        rows.append(row)

    return headers, rows


def peak_intensity_summary(
    x0: float,
    traces: Sequence[dict],
    *,
    max_traces: int = 4,
) -> str:
    """Compact intensity summary for visible traces."""
    if not traces:
        return ""

    parts: list[str] = []

    for trace in list(traces)[:max_traces]:
        label = str(trace.get("label", "trace"))
        y = nearest_y_for_trace(trace, x0)

        if np.isfinite(y):
            parts.append(f"{label}: {y:.3g}")
        else:
            parts.append(f"{label}: nan")

    if len(traces) > max_traces:
        parts.append(f"+{len(traces) - max_traces} more")

    return " | ".join(parts)


def robust_ylim_for_traces(
    traces: Sequence[dict],
    *,
    xlim: tuple[float, float],
    lower: float = 1.0,
    upper: float = 99.5,
    pad: float = 0.08,
) -> tuple[float, float] | None:
    """Return robust y-limits for visible traces inside an x-range."""
    ys: list[np.ndarray] = []

    xmin, xmax = float(min(xlim)), float(max(xlim))

    for trace in traces:
        x, y = trace_xy(trace)

        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)

        finite = np.isfinite(x) & np.isfinite(y)

        if not np.any(finite):
            continue

        x = x[finite]
        y = y[finite]

        mask = (x >= xmin) & (x <= xmax)

        if np.any(mask):
            y = y[mask]

        if y.size:
            ys.append(y)

    if not ys:
        return None

    yy = np.concatenate(ys)

    if yy.size < 3:
        return None

    lo = float(np.nanpercentile(yy, lower))
    hi = float(np.nanpercentile(yy, upper))

    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return None

    margin = (hi - lo) * float(pad)
    return lo - margin, hi + margin