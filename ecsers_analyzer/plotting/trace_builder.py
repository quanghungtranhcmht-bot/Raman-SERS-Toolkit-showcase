from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import numpy as np


Trace = dict[str, Any]


def make_trace(
    *,
    spec: Any,
    label: str,
    role: str,
    file: str = "",
    visible: bool = True,
    color_index: int = 0,
) -> Trace:
    """Create one plot-trace dictionary.

    This intentionally returns a dict for now because the current UI table
    already expects dict-like traces. Later we can upgrade this to a dataclass.
    """
    return {
        "spec": spec,
        "label": label,
        "role": role,
        "file": file,
        "visible": visible,
        "color_index": color_index,
    }


def build_single_traces(
    *,
    raw_spec: Any,
    processed_spec: Any,
    file_name: str = "",
    show_raw: bool = True,
    show_processed: bool = True,
    show_baseline: bool = False,
) -> list[Trace]:
    """Build trace dictionaries for single-spectrum plotting."""
    traces: list[Trace] = []

    if raw_spec is not None and show_raw:
        traces.append(
            make_trace(
                spec=raw_spec,
                label="Raw",
                role="raw",
                file=file_name,
                visible=True,
                color_index=0,
            )
        )

    if processed_spec is not None and show_processed:
        traces.append(
            make_trace(
                spec=processed_spec,
                label="Processed",
                role="processed",
                file=file_name,
                visible=True,
                color_index=1,
            )
        )

    if (
        processed_spec is not None
        and show_baseline
        and getattr(processed_spec, "baseline", None) is not None
    ):
        traces.append(
            make_trace(
                spec=processed_spec,
                label="Estimated baseline",
                role="baseline",
                file=file_name,
                visible=True,
                color_index=2,
            )
        )

    return traces


def build_batch_traces(
    *,
    specs: Sequence[Any],
    labels: Sequence[str],
    files: Sequence[Any],
    mode: str,
) -> list[Trace]:
    """Build trace dictionaries for batch overlay/stacked plotting."""
    mode = str(mode or "overlay").lower()
    role = "ref-sub processed" if mode == "reference_subtracted_stacked" else "processed"

    traces: list[Trace] = []

    for i, (spec, label, path) in enumerate(zip(specs, labels, files)):
        try:
            file_name = Path(path).name
        except Exception:
            file_name = str(path or "")

        traces.append(
            make_trace(
                spec=spec,
                label=str(label),
                role=role,
                file=file_name,
                visible=True,
                color_index=i,
            )
        )

    return traces


def trace_xy(trace: Trace) -> tuple[np.ndarray, np.ndarray]:
    """Return x/y arrays for Raman/SERS or PAAX/electrochemistry traces."""
    if str(trace.get("kind", "")).lower() == "paax":
        paax_trace = trace.get("trace", None)

        if paax_trace is None:
            return np.array([], dtype=float), np.array([], dtype=float)

        try:
            x = np.asarray(paax_trace.x, dtype=float)
            y = np.asarray(paax_trace.y, dtype=float)
        except Exception:
            return np.array([], dtype=float), np.array([], dtype=float)

        return x, y

    spec = trace.get("spec", None)

    if spec is None:
        return np.array([], dtype=float), np.array([], dtype=float)

    role = str(trace.get("role", "")).lower()

    if role == "raw":
        return np.asarray(spec.x_raw, dtype=float), np.asarray(spec.y_raw, dtype=float)

    if role == "baseline":
        return np.asarray(spec.x_raw, dtype=float), np.asarray(spec.baseline, dtype=float)

    return np.asarray(spec.x, dtype=float), np.asarray(spec.y, dtype=float)


def stack_offset_value_from_traces(
    traces: Sequence[Trace],
    *,
    xlim: tuple[float, float] | None = None,
    stack_offset_text: str = "auto",
) -> float:
    """Calculate stacked-plot vertical offset.

    If stack_offset_text is a positive number, use it directly.
    Otherwise calculate 1.20 × the largest y-range inside xlim.
    """
    txt = str(stack_offset_text or "auto").strip().lower()

    if txt != "auto":
        try:
            val = float(txt)
            if val > 0:
                return val
        except Exception:
            pass

    ranges: list[float] = []

    for tr in traces:
        x, y = trace_xy(tr)

        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)

        finite = np.isfinite(x) & np.isfinite(y)

        if not np.any(finite):
            continue

        x = x[finite]
        y = y[finite]

        if xlim is not None:
            lo, hi = float(min(xlim)), float(max(xlim))
            mask = (x >= lo) & (x <= hi)
            yy = y[mask] if np.any(mask) else y
        else:
            yy = y

        yy = yy[np.isfinite(yy)]

        if yy.size:
            ranges.append(float(np.nanmax(yy) - np.nanmin(yy)))

    if not ranges:
        return 1.0

    offset = max(ranges) * 1.20
    return offset if offset > 0 else 1.0


def stack_offset_value(
    specs: Sequence[Any],
    *,
    xlim: tuple[float, float] | None = None,
    stack_offset_text: str = "auto",
) -> float:
    traces = [
        make_trace(
            spec=spec,
            label="",
            role="processed",
            file="",
            visible=True,
            color_index=i,
        )
        for i, spec in enumerate(specs)
    ]

    return stack_offset_value_from_traces(
        traces,
        xlim=xlim,
        stack_offset_text=stack_offset_text,
    )


def axis_y_label_for_spec(spec: Any) -> str:
    """Return Raman y-axis label from the spectrum normalization state."""
    if spec is None:
        return "Intensity (a.u.)"

    norm = str(getattr(spec, "normalization_method", "") or "").lower()

    if norm in ("power_time", "power*time"):
        return "Intensity (ADU mW⁻¹ s⁻¹)"

    if norm in ("max", "area", "vector", "l2"):
        return "Normalized Intensity (a.u.)"

    return "Intensity (a.u.)"