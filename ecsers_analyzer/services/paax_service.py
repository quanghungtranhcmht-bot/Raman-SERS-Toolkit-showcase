from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ecsers_analyzer.ec.trace_plan import (
    list_studies,
    paax_file_summary,
    paax_plot_trace_dict,
    paax_status_loaded,
    paax_status_plotted,
    selected_trace_from_visible,
    study_name,
    trace_arrays,
    trace_dropdown_labels,
    trace_has_data,
    trace_has_finite_data,
    trace_meta,
    trace_name,
    traces_for_study,
    x_label,
    y_label,
)


@dataclass(frozen=True)
class PaaxLoadedFilePlan:
    studies: list[str]
    file_label: str
    status_message: str


@dataclass(frozen=True)
class PaaxTraceDropdownPlan:
    visible_traces: list[Any]
    dropdown_labels: list[str]


@dataclass(frozen=True)
class PaaxPlotPlan:
    ok: bool
    trace: Any = None
    x: Any = None
    y: Any = None
    name: str = ""
    xlabel: str = ""
    ylabel: str = ""
    trace_dict: dict | None = None
    status_message: str = ""
    error_title: str = ""
    error_message: str = ""


class PaaxService:
    """Backend service for PAAX trace organization and plot planning.

    This service has no PySide6 dependency.
    The Qt frontend owns widgets, dialogs, message boxes, and PyQtGraph drawing.
    """

    def loaded_file_plan(
        self,
        *,
        path: str | Path | None,
        traces: list[Any],
    ) -> PaaxLoadedFilePlan:
        return PaaxLoadedFilePlan(
            studies=list_studies(traces),
            file_label=paax_file_summary(path, traces),
            status_message=paax_status_loaded(path) if path is not None else f"Loaded {len(traces)} trace(s).",
        )

    def dropdown_plan(
        self,
        *,
        traces: list[Any],
        selected_study: str,
    ) -> PaaxTraceDropdownPlan:
        visible = traces_for_study(traces, selected_study)

        return PaaxTraceDropdownPlan(
            visible_traces=visible,
            dropdown_labels=trace_dropdown_labels(visible),
        )

    def selected_trace(
        self,
        *,
        visible_traces: list[Any],
        selected_index: int,
    ) -> Any | None:
        return selected_trace_from_visible(
            visible_traces,
            selected_index,
        )

    def plot_plan(
        self,
        *,
        trace: Any,
        source_path: str | Path | None = None,
        color_index: int = 0,
    ) -> PaaxPlotPlan:
        if trace is None:
            return PaaxPlotPlan(
                ok=False,
                error_title="No PAAX trace",
                error_message="Open a PAAX file and choose a trace first.",
            )

        try:
            x, y = trace_arrays(trace)
        except Exception as exc:
            return PaaxPlotPlan(
                ok=False,
                error_title="Plot failed",
                error_message=str(exc),
            )

        if not trace_has_data(trace):
            return PaaxPlotPlan(
                ok=False,
                error_title="Empty trace",
                error_message="The selected PAAX trace contains no data.",
            )

        if not trace_has_finite_data(trace):
            return PaaxPlotPlan(
                ok=False,
                error_title="Invalid trace",
                error_message="The selected PAAX trace contains no finite numeric data.",
            )

        return PaaxPlotPlan(
            ok=True,
            trace=trace,
            x=x,
            y=y,
            name=trace_name(trace),
            xlabel=x_label(trace),
            ylabel=y_label(trace),
            trace_dict=paax_plot_trace_dict(
                trace,
                source_path=source_path,
                color_index=color_index,
            ),
            status_message=paax_status_plotted(trace),
        )

    def finite_ranges(self, x, y) -> tuple[tuple[float, float] | None, tuple[float, float] | None]:
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)

        finite_x = x[np.isfinite(x)]
        finite_y = y[np.isfinite(y)]

        x_range = None
        y_range = None

        if finite_x.size:
            x_range = (float(np.nanmin(finite_x)), float(np.nanmax(finite_x)))

        if finite_y.size:
            y_range = (float(np.nanmin(finite_y)), float(np.nanmax(finite_y)))

        return x_range, y_range

    # Small label helpers keep the UI from importing trace_plan directly.
    def study_name(self, trace: Any) -> str:
        return study_name(trace)

    def trace_name(self, trace: Any) -> str:
        return trace_name(trace)

    def x_label(self, trace: Any) -> str:
        return x_label(trace)

    def y_label(self, trace: Any) -> str:
        return y_label(trace)

    def trace_meta(self, trace: Any, key: str, default: Any = "") -> Any:
        return trace_meta(trace, key, default)