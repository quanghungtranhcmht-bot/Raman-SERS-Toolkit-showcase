from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np

from ecsers_analyzer.ec.trace_plan import (
    finite_trace_arrays,
    paax_metadata_rows,
    study_name,
    trace_arrays,
    trace_name,
    x_label,
    y_label,
)

def export_paax_trace_csv(
    trace: Any,
    out_path: str | Path,
) -> Path:
    """Export one PAAX trace to CSV.

    Keeps the current UI behavior:
    first row = x label, y label
    remaining rows = x, y numeric values
    """
    out = Path(out_path)

    xlabel = x_label(trace)
    ylabel = y_label(trace)
    x, y = trace_arrays(trace)

    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([xlabel, ylabel])

        for xi, yi in zip(x, y):
            writer.writerow([float(xi), float(yi)])

    return out


def export_paax_trace_excel(
    trace: Any,
    out_path: str | Path,
    *,
    source_path: str | Path | None = None,
) -> Path:
    """Export one PAAX trace to an Excel workbook.

    This preserves the current Qt UI workbook layout:
    - ec_trace sheet
    - metadata sheet
    - plot sheet
    - scatter chart with no gridlines
    """
    try:
        import xlsxwriter
    except Exception as exc:
        raise ImportError(
            "PAAX Excel export requires xlsxwriter.\n\n"
            "Install it with:\npython -m pip install xlsxwriter"
        ) from exc

    out = Path(out_path)

    study = study_name(trace)
    name = trace_name(trace)
    xlabel = x_label(trace)
    ylabel = y_label(trace)

    x, y = finite_trace_arrays(trace)

    if x.size == 0 or y.size == 0:
        raise ValueError("The selected PAAX trace contains no finite numeric data.")

    wb = xlsxwriter.Workbook(str(out))

    header_fmt = wb.add_format({"bold": True})
    meta_key_fmt = wb.add_format({"bold": True})
    number_fmt = wb.add_format({"num_format": "0.000000"})

    # ---------------- data sheet ----------------
    ws = wb.add_worksheet("ec_trace")
    ws.write_row(0, 0, [xlabel, ylabel], header_fmt)

    for i, (xi, yi) in enumerate(zip(x, y), start=1):
        ws.write_number(i, 0, float(xi), number_fmt)
        ws.write_number(i, 1, float(yi), number_fmt)

    ws.freeze_panes(1, 0)
    ws.set_column(0, 1, 18)

    # ---------------- metadata sheet ----------------
    ws_md = wb.add_worksheet("metadata")

    rows = paax_metadata_rows(
        trace,
        source_path=source_path,
        finite_only=True,
    )

    ws_md.write_row(0, 0, ["key", "value"], header_fmt)

    for r, (k, v) in enumerate(rows, start=1):
        ws_md.write(r, 0, k, meta_key_fmt)

        if isinstance(v, (int, float)) and np.isfinite(v):
            ws_md.write_number(r, 1, float(v))
        else:
            ws_md.write(r, 1, str(v))

    ws_md.freeze_panes(1, 0)
    ws_md.set_column(0, 0, 26)
    ws_md.set_column(1, 1, 45)

    # ---------------- plot sheet ----------------
    ws_plot = wb.add_worksheet("plot")

    nrows = len(x) + 1

    chart = wb.add_chart({"type": "scatter", "subtype": "straight"})

    chart.add_series({
        "name": name,
        "categories": ["ec_trace", 1, 0, nrows - 1, 0],
        "values": ["ec_trace", 1, 1, nrows - 1, 1],
        "marker": {"type": "none"},
        "line": {"width": 1.75},
    })

    chart.set_title({"name": f"{study} — {name}"})
    chart.set_legend({"none": True})

    chart.set_x_axis({
        "name": xlabel,
        "num_format": "0",
        "major_tick_mark": "outside",
        "minor_tick_mark": "none",
        "major_gridlines": {"visible": False},
        "num_font": {"size": 12},
        "name_font": {"size": 12},
    })

    chart.set_y_axis({
        "name": ylabel,
        "num_format": "0.00",
        "major_tick_mark": "outside",
        "minor_tick_mark": "none",
        "major_gridlines": {"visible": False},
        "num_font": {"size": 12},
        "name_font": {"size": 12},
    })

    chart.set_chartarea({"border": {"none": True}})
    chart.set_plotarea({"border": {"none": True}})
    chart.set_size({"width": 920, "height": 420})
    chart.set_plotarea({
        "layout": {
            "x": 0.11,
            "y": 0.08,
            "width": 0.84,
            "height": 0.80,
        }
    })

    ws_plot.insert_chart("A1", chart)

    wb.close()

    return out