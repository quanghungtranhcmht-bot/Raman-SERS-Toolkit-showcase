from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

import numpy as np

def _excel_x_axis_label() -> str:
    """Excel-safe x-axis label."""
    return "Raman Shift (cm⁻¹)"


def _excel_y_axis_label_for_spec(spec) -> str:
    """Dynamic Excel y-axis label based on normalization."""
    norm = str(getattr(spec, "normalization_method", "") or "").lower()

    if norm in ("power_time", "power*time"):
        return "Intensity (ADU mW⁻¹ s⁻¹)"

    if norm in ("max", "area", "vector", "l2"):
        return "Normalized Intensity (a.u.)"

    return "Intensity (a.u.)"


def _excel_y_axis_label_for_overlay(spectra) -> str:
    """Use one y-axis label for overlay. If mixed normalization, use generic label."""
    labels = {
        _excel_y_axis_label_for_spec(s)
        for s in spectra
    }

    if len(labels) == 1:
        return labels.pop()

    return "Processed Intensity (a.u.)"


def _excel_x_limits(x, xlim):
    """Return exact Excel x-axis limits.

    Uses GUI/export xlim directly when provided, so 400–1700 stays exact.
    """
    x = np.asarray(x, dtype=float)

    if xlim:
        return float(min(xlim)), float(max(xlim))

    return float(np.nanmin(x)), float(np.nanmax(x))


def _excel_roi_mask(x, xlim):
    """Mask for y-axis scaling inside the requested x-range."""
    x = np.asarray(x, dtype=float)

    if not xlim:
        return np.ones_like(x, dtype=bool)

    lo, hi = float(min(xlim)), float(max(xlim))
    return (x >= lo) & (x <= hi)


def _xlsxwriter_x_axis_options(x, xlim, fontsize):
    x_min, x_max = _excel_x_limits(x, xlim)

    return {
        "name": _excel_x_axis_label(),
        "min": x_min,
        "max": x_max,
        "num_format": "0",
        "major_tick_mark": "outside",
        "minor_tick_mark": "none",
        "major_gridlines": {"visible": False},
        "name_font": {"size": fontsize},
        "num_font": {"size": fontsize},
    }


def _xlsxwriter_y_axis_options(y_axis_label, y_min=None, y_max=None, y_lock=True, fontsize=12):
    opts = {
        "name": y_axis_label,
        "label_position": "none",
        "major_tick_mark": "outside",
        "minor_tick_mark": "none",
        "major_gridlines": {"visible": False},
        "name_font": {"size": fontsize},
        "num_font": {"size": fontsize},
    }

    if y_lock and y_max is not None:
        opts["max"] = float(y_max)
        opts["min"] = float(y_min) if y_min is not None else 0.0

    return opts

# -----------------------------
# Batch export with overlay chart
# -----------------------------

def export_batch_excel(
    spectra,
    out_path,
    *,
    xlim=(200, 2000),
    batch_plot_mode="overlay",
    stack_offset=None,
    y_lock=True,
    fontsize=12,
    chart_title_mode="blank",
    chart_title_text="",
    overlay_legend=False,
    overlay_labels=None,
    overlay_title=None,
    per_sheet_titles=None,
    y_axis_label_override=None,
    common_grid="first",
    grid_step=1.0,
):
    """Export many processed spectra into ONE Excel workbook.

    Creates:
      - summary: metadata + QC metrics
      - overlay: data table + Excel-native overlay chart
      - one sheet per spectrum: data + its own chart

    Requires xlsxwriter.
    """
    import math
    import re

    try:
        import xlsxwriter  # noqa: F401
    except Exception as e:
        raise ImportError("Batch Excel export requires xlsxwriter. Install with: python -m pip install xlsxwriter") from e

    import xlsxwriter

    spectra = list(spectra or [])
    if len(spectra) == 0:
        raise ValueError("No spectra provided for batch export")

    def roi_mask(x, lim):
        if not lim:
            return np.ones_like(x, dtype=bool)
        a, b = float(lim[0]), float(lim[1])
        lo, hi = (a, b) if a <= b else (b, a)
        return (x >= lo) & (x <= hi)

    def safe_sheet(name, used):
        s = re.sub(r'[:\\/?*\[\]]', "_", str(name or "").strip())
        if not s:
            s = "sheet"
        s = s[:31]
        if s not in used:
            used.add(s)
            return s
        i = 2
        while True:
            suffix = f"_{i}"
            base = s[: (31 - len(suffix))]
            cand = base + suffix
            if cand not in used:
                used.add(cand)
                return cand
            i += 1

    # Build common x-grid for overlay
    if common_grid == "linspace":
        xmin, xmax = float(xlim[0]), float(xlim[1])
        step = float(grid_step)
        if step <= 0:
            raise ValueError("grid_step must be > 0")
        n = int(math.floor((xmax - xmin) / step)) + 1
        x_grid = np.linspace(xmin, xmax, n)
    else:
        x0 = np.asarray(spectra[0].x, dtype=float)
        m0 = roi_mask(x0, xlim)
        if not np.any(m0):
            raise ValueError("First spectrum has no points within xlim; cannot build overlay grid")
        x_grid = x0[m0].copy()

    # Optional legend labels from UI
    provided_labels = None
    if overlay_labels is not None and len(overlay_labels) == len(spectra):
        provided_labels = [str(x) for x in overlay_labels]

    labels = []
    y_cols = []
    summary_rows = []

    for i, spec in enumerate(spectra, start=1):
        label_i = None
        if provided_labels is not None:
            label_i = provided_labels[i - 1]
        else:
            md = getattr(spec, "metadata", {}) or {}
            label_i = md.get("legend_label") or md.get("filename_stem")
            if not label_i:
                label_i = getattr(spec, "title_string", lambda: "")() or f"Spectrum_{i}"
        label_i = str(label_i)
        x = np.asarray(spec.x, dtype=float)
        y = np.asarray(spec.y, dtype=float)
        m = roi_mask(x, xlim)
        if np.any(m):
            xs = x[m]
            ys = y[m]
            order = np.argsort(xs)
            xs = xs[order]
            ys = ys[order]
            yi = np.interp(x_grid, xs, ys, left=np.nan, right=np.nan)
        else:
            yi = np.full_like(x_grid, np.nan, dtype=float)
        y_cols.append(yi)
        labels.append(label_i)

        md = dict(getattr(spec, "metadata", {}) or {})
        summary_rows.append(md)

    y_stack = np.vstack(y_cols)
    y_max = float(np.nanmax(y_stack)) if np.isfinite(y_stack).any() else 1.0
    y_max = y_max * 1.05 if y_max > 0 else 1.0

    plot_mode = (batch_plot_mode or "overlay").lower()
    custom_ylabel = str(y_axis_label_override or "").strip()

    if plot_mode in ("stacked", "reference_subtracted_stacked"):
        try:
            offset = float(stack_offset)
        except Exception:
            offset = 0.0

        if offset <= 0:
            ranges = []
            for col in y_cols:
                yy = np.asarray(col, dtype=float)
                yy = yy[np.isfinite(yy)]
                if yy.size:
                    ranges.append(float(np.nanmax(yy) - np.nanmin(yy)))
            offset = max(ranges) * 1.20 if ranges else 1.0
            if offset <= 0:
                offset = 1.0

        plot_y_cols = [
            np.asarray(col, dtype=float) + i * offset
            for i, col in enumerate(y_cols)
        ]

        base_ylabel = custom_ylabel or _excel_y_axis_label_for_overlay(spectra)
        if plot_mode == "reference_subtracted_stacked":
            plot_ylabel = f"Reference-subtracted {base_ylabel} + offset"
            plot_sheet_name = "ref_sub_stacked"
        else:
            plot_ylabel = f"{base_ylabel} + offset"
            plot_sheet_name = "stacked"
    else:
        plot_y_cols = y_cols
        plot_ylabel = custom_ylabel or _excel_y_axis_label_for_overlay(spectra)
        plot_sheet_name = "overlay"

    plot_y_stack = np.vstack(plot_y_cols)
    plot_y_min = float(np.nanmin(plot_y_stack)) if np.isfinite(plot_y_stack).any() else 0.0
    plot_y_max = float(np.nanmax(plot_y_stack)) if np.isfinite(plot_y_stack).any() else 1.0

    plot_y_min = plot_y_min * 1.05 if plot_y_min < 0 else 0.0
    plot_y_max = plot_y_max * 1.05 if plot_y_max > 0 else 1.0

    out_path = str(out_path)
    wb = xlsxwriter.Workbook(out_path)
    header = wb.add_format({"bold": True})
    
    # ---- summary sheet ----
    ws_sum = wb.add_worksheet("summary")
    cols = [
    "filename_stem",
    "sample_code",
    "analyte",
    "analyte_concentration_M",
    "aggregating_salt",
    "salt_concentration_M",
    "electrolyte",
    "solvent",
    "substrate",
    "potential_label",
    "replicate",
    "condition",
    "laser_nm",
    "objective",
    "integration_time_s",
    "laser_power_mw",
    "legend_label",
    "background_correction",
    "reference_file",
    "reference_subtraction_stage",
]
    ws_sum.write_row(0, 0, cols, header)
    for r, row in enumerate(summary_rows, start=1):
        for c, k in enumerate(cols):
            v = row.get(k, "")
            if isinstance(v, (int, float)) and np.isfinite(v):
                ws_sum.write_number(r, c, float(v))
            else:
                ws_sum.write(r, c, str(v))
    ws_sum.freeze_panes(1, 0)

    # ---- overlay sheet (data + chart) ----
    ws_ov = wb.add_worksheet(plot_sheet_name)
    ws_ov.write_row(0, 0, ["raman_shift_cm-1"] + labels, header)
    for i, xv in enumerate(x_grid, start=1):
        ws_ov.write_number(i, 0, float(xv))
        for j, col in enumerate(plot_y_cols, start=1):
            yv = col[i - 1]
            if np.isfinite(yv):
                ws_ov.write_number(i, j, float(yv))
            else:
                ws_ov.write_blank(i, j, None)

    chart = wb.add_chart({"type": "scatter", "subtype": "straight"})
    nrows = len(x_grid) + 1
    for j, label in enumerate(labels, start=1):
        chart.add_series({
            "name": label,
            "categories": [plot_sheet_name, 1, 0, nrows - 1, 0],
            "values": [plot_sheet_name, 1, j, nrows - 1, j],
            "marker": {"type": "none"},
            "line": {"width": 1.5},
        })

    mode = str(chart_title_mode).lower()
    ttxt = ""
    if overlay_title is not None:
        ttxt = str(overlay_title).strip()
    if not ttxt and mode == "custom":
        ttxt = str(chart_title_text or "").strip()
    if not ttxt and mode == "sample":
        ttxt = "Overlay"

    if ttxt:
        chart.set_title({"name": ttxt})
    else:
        chart.set_title({"none": True})

    if overlay_legend:
        chart.set_legend({"position": "right"})
    else:
        chart.set_legend({"none": True})

    # Excel-specific overlay axis labels and formatting

    chart.set_x_axis(
        _xlsxwriter_x_axis_options(
            x=x_grid,
            xlim=xlim,
            fontsize=fontsize,
        )
    )

    chart.set_y_axis(
        _xlsxwriter_y_axis_options(
            y_axis_label=plot_ylabel,
            y_min=plot_y_min,
            y_max=plot_y_max,
            y_lock=y_lock,
            fontsize=fontsize,
        )
    )

    chart.set_chartarea({"border": {"none": True}})
    chart.set_plotarea({"border": {"none": True}})
    chart.set_size({"width": 980, "height": 430})
    chart.set_plotarea({"layout": {"x": 0.11, "y": 0.08, "width": 0.82, "height": 0.80}})

    ws_ov.insert_chart("H2", chart)

    # ---- one sheet per spectrum (data + chart) ----
    used = {"summary", plot_sheet_name}
    titles_list = None
    if per_sheet_titles is not None and len(per_sheet_titles) == len(spectra):
        titles_list = [str(t) for t in per_sheet_titles]

    for i, spec in enumerate(spectra, start=1):
        label_i = labels[i - 1] if i - 1 < len(labels) else (getattr(spec, "title_string", lambda: "")() or f"s{i}")
        sheet = safe_sheet(str(label_i), used)
        ws = wb.add_worksheet(sheet)

        x = np.asarray(spec.x, dtype=float)
        y = np.asarray(spec.y, dtype=float)
        ws.write_row(0, 0, ["raman_shift_cm-1", "intensity"], header)
        for r, (xi, yi) in enumerate(zip(x, y), start=1):
            ws.write_number(r, 0, float(xi))
            ws.write_number(r, 1, float(yi))

        c = wb.add_chart({"type": "scatter", "subtype": "straight"})
        nrows = len(x) + 1
        c.add_series({
            "name": str(label_i),
            "categories": [sheet, 1, 0, nrows - 1, 0],
            "values": [sheet, 1, 1, nrows - 1, 1],
            "marker": {"type": "none"},
            "line": {"width": 2.0},
        })

        # Per-sheet title resolution
        t = ""
        if titles_list is not None:
            t = str(titles_list[i - 1]).strip()
        if not t and mode == "custom":
            t = str(chart_title_text or "").strip()
        if not t and mode == "sample":
            t = str(label_i)
        if t:
            c.set_title({"name": t})
        else:
            c.set_title({"none": True})
        c.set_legend({"none": True})

        ylabel = custom_ylabel or _excel_y_axis_label_for_spec(spec)

        xr = _excel_roi_mask(x, xlim)
        y_roi = y[xr] if np.any(xr) else y
        y_m = float(np.nanmax(y_roi)) if y_roi.size else float(np.nanmax(y))
        y_m = y_m * 1.05 if (np.isfinite(y_m) and y_m > 0) else 1.0

        c.set_x_axis(
            _xlsxwriter_x_axis_options(
                x=x,
                xlim=xlim,
                fontsize=fontsize,
            )
        )

        c.set_y_axis(
            _xlsxwriter_y_axis_options(
                y_axis_label=ylabel,
                y_max=y_m,
                y_lock=y_lock,
                fontsize=fontsize,
            )
        )

        c.set_chartarea({"border": {"none": True}})
        c.set_plotarea({"border": {"none": True}})
        c.set_size({"width": 920, "height": 420})
        c.set_plotarea({"layout": {"x": 0.11, "y": 0.08, "width": 0.84, "height": 0.80}})

        ws.insert_chart("D2", c)

    wb.close()
    return out_path

def export_single_spectrum_excel(
        spec: Any,
        out_path: str | Path,
        *,
        include_chart: bool = True,
        include_metadata: bool = True,
        engine: str = "auto",
        xlim: tuple[float, float] | None = (200, 2000),
        y_lock: bool = True,
        fontsize: int = 12,
        chart_title_mode: str = "blank",
        chart_title_text: str = "",
        y_axis_label_override: str | None = None,
    ) -> str:
        """
        Export processed spectrum + metadata + preprocessing params to Excel.
        Creates an Excel-native XY scatter chart (publication-style).

        engine:
          - "auto" (prefer xlsxwriter for charts)
          - "xlsxwriter"
          - "openpyxl"
        """
        out_path = str(out_path)

        # Prepare tables
        x = np.asarray(spec.x, dtype=float)
        y = np.asarray(spec.y, dtype=float)

        # metadata rows
        md_items = sorted((spec.metadata or {}).items(), key=lambda kv: kv[0])
        md_rows = [(k, str(v)) for k, v in md_items]

        # ------------------ prefer xlsxwriter ------------------
        if engine in ("auto", "xlsxwriter"):
            try:
                import xlsxwriter  # noqa: F401
                use_xlsxwriter = True
            except Exception:
                use_xlsxwriter = False

            if use_xlsxwriter:
                import xlsxwriter
                wb = xlsxwriter.Workbook(out_path)
                ws = wb.add_worksheet("spectrum")
                ws_md = wb.add_worksheet("metadata") if include_metadata else None
                ws_pp = wb.add_worksheet("preprocess")
                # write spectrum header
                ws.write_row(0, 0, ["raman_shift_cm-1", "intensity"])
                for i in range(len(x)):
                    ws.write_number(i+1, 0, float(x[i]))
                    ws.write_number(i+1, 1, float(y[i]))

                # write metadata
                if include_metadata and ws_md is not None:
                    ws_md.write_row(0, 0, ["key", "value"])
                    for i, (k, v) in enumerate(md_rows, start=1):
                        ws_md.write(i, 0, k)
                        ws_md.write(i, 1, v)

                # preprocess params
                ws_pp.write_row(0, 0, ["key", "value"])
                ws_pp.write(1, 0, "baseline_method")
                ws_pp.write(1, 1, str(spec.metadata.get("baseline_method", "")))
                ws_pp.write(2, 0, "normalization")
                ws_pp.write(2, 1, str(spec.normalization_method))

                if include_chart:
                    ws_plot = wb.add_worksheet("plot")
                    nrows = len(x) + 1
                    chart = wb.add_chart({"type": "scatter", "subtype": "straight"})
                    chart.add_series({
                        "name": (spec.metadata.get("filename_stem") or "Processed"),
                        "categories": ["spectrum", 1, 0, nrows-1, 0],
                        "values": ["spectrum", 1, 1, nrows-1, 1],
                        "marker": {"type": "none"},
                        "line": {"width": 2.25},
                    })

                    title_mode = str(chart_title_mode).lower()
                    title_txt = str(chart_title_text or "").strip()
                    if title_txt:
                        chart.set_title({"name": title_txt})
                    elif title_mode == "sample" and spec.metadata.get("filename_stem"):
                        chart.set_title({"name": str(spec.metadata.get("filename_stem"))})
                    else:
                        chart.set_title({"none": True})

                    chart.set_legend({"none": True})

                    # Excel-specific axis labels and formatting
                    ylabel = str(y_axis_label_override or "").strip() or _excel_y_axis_label_for_spec(spec)

                    xr = _excel_roi_mask(x, xlim)
                    y_roi = y[xr] if np.any(xr) else y
                    y_max = float(np.nanmax(y_roi)) if y_roi.size else float(np.nanmax(y))
                    y_max = y_max * 1.05 if (np.isfinite(y_max) and y_max > 0) else 1.0

                    chart.set_x_axis(
                        _xlsxwriter_x_axis_options(
                            x=x,
                            xlim=xlim,
                            fontsize=fontsize,
                        )
                    )

                    chart.set_y_axis(
                        _xlsxwriter_y_axis_options(
                            y_axis_label=ylabel,
                            y_max=y_max,
                            y_lock=y_lock,
                            fontsize=fontsize,
                        )
                    )

                    chart.set_chartarea({"border": {"none": True}})
                    chart.set_plotarea({"border": {"none": True}})
                    chart.set_size({"width": 920, "height": 420})
                    chart.set_plotarea({"layout": {"x": 0.11, "y": 0.08, "width": 0.84, "height": 0.80}})
                    ws_plot.insert_chart("A1", chart)

                wb.close()
                return out_path

        # ------------------ openpyxl fallback ------------------
        try:
            import openpyxl
            from openpyxl import Workbook
            from openpyxl.chart import ScatterChart, Reference, Series
        except Exception as e:
            raise ImportError(
                "To export Excel with a native chart, install xlsxwriter (recommended) or openpyxl. "
                "Try: python -m pip install xlsxwriter"
            ) from e

        wb = Workbook()
        # remove default sheet
        wb.remove(wb.active)
        ws = wb.create_sheet("spectrum")
        ws_md = None
        if include_metadata:
            ws_md = wb.create_sheet("metadata")
        ws_pp = wb.create_sheet("preprocess")

        ws.append(["raman_shift_cm-1", "intensity"])
        for xi, yi in zip(x, y):
            ws.append([float(xi), float(yi)])

        if include_metadata and ws_md is not None:
            ws_md.append(["key", "value"])
            for k, v in md_rows:
                ws_md.append([k, v])

        ws_pp.append(["key", "value"])
        ws_pp.append(["normalization", str(spec.normalization_method)])

        if include_chart:
            ws_plot = wb.create_sheet("plot")
            chart = ScatterChart()
            chart.legend = None
            chart.title = None

            # References (skip header)
            x_ref = Reference(ws, min_col=1, min_row=2, max_row=len(x)+1)
            y_ref = Reference(ws, min_col=2, min_row=2, max_row=len(y)+1)
            series = Series(y_ref, x_ref, title="Processed")

            # ✅ FIX: do NOT construct GraphicalProperties(line=...)
            # Set line/marker safely across openpyxl versions
            try:
                series.marker = None
            except Exception:
                pass
            try:
                # Many versions:
                # series.graphicalProperties.line.width = ...
                gp = series.graphicalProperties
                # some versions use .line, others .ln
                if hasattr(gp, "line") and gp.line is not None:
                    gp.line.width = 20000  # approx 2pt
                elif hasattr(gp, "ln") and gp.ln is not None:
                    gp.ln.w = 20000
                else:
                    # create if missing
                    try:
                        from openpyxl.drawing.line import LineProperties
                        lp = LineProperties(w=20000)
                        if hasattr(gp, "line"):
                            gp.line = lp
                        else:
                            gp.ln = lp
                    except Exception:
                        pass
            except Exception:
                pass

            chart.series.append(series)

            chart.x_axis.title = _excel_x_axis_label()
            chart.y_axis.title = str(y_axis_label_override or "").strip() or _excel_y_axis_label_for_spec(spec)

            try:
                x_min, x_max = _excel_x_limits(x, xlim)
                chart.x_axis.scaling.min = x_min
                chart.x_axis.scaling.max = x_max
                chart.x_axis.numFmt = "0"
                chart.x_axis.majorTickMark = "out"
                chart.x_axis.minorTickMark = "none"

                chart.y_axis.tickLblPos = "none"
                chart.y_axis.majorTickMark = "out"
                chart.y_axis.minorTickMark = "none"
            except Exception:
                pass
            # remove gridlines
            try:
                chart.x_axis.majorGridlines = None
                chart.y_axis.majorGridlines = None
            except Exception:
                pass

            # size
            chart.width = 28
            chart.height = 12

            ws_plot.add_chart(chart, "A1")

        wb.save(out_path)
        return out_path