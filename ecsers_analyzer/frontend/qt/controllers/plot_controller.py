from __future__ import annotations

from pathlib import Path
from typing import Any

import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets

from ecsers_analyzer.plotting.trace_builder import trace_xy


class PlotController:
    """Qt/PyQtGraph plot-view controller.

    This controller owns frontend plot coordination only.
    Scientific processing, import/export, and library matching stay in services.
    Peak and ROI interaction methods still live on the main window for now.
    """

    def __init__(self, window):
        self.window = window

    def refresh_trace_table(self):
        w = self.window

        if not hasattr(w, "trace_table"):
            return

        w._updating_trace_table = True
        w.trace_table.setRowCount(len(w.traces))

        for row, tr in enumerate(w.traces):
            show_item = QtWidgets.QTableWidgetItem("")
            show_item.setFlags(
                QtCore.Qt.ItemFlag.ItemIsEnabled
                | QtCore.Qt.ItemFlag.ItemIsUserCheckable
            )
            show_item.setCheckState(
                QtCore.Qt.CheckState.Checked
                if tr.get("visible", True)
                else QtCore.Qt.CheckState.Unchecked
            )
            w.trace_table.setItem(row, 0, show_item)

            label_item = QtWidgets.QTableWidgetItem(str(tr.get("label", "")))
            label_item.setFlags(label_item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
            w.trace_table.setItem(row, 1, label_item)

            role_item = QtWidgets.QTableWidgetItem(str(tr.get("role", "")))
            role_item.setFlags(role_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            w.trace_table.setItem(row, 2, role_item)

            file_item = QtWidgets.QTableWidgetItem(str(tr.get("file", "")))
            file_item.setFlags(file_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            w.trace_table.setItem(row, 3, file_item)

            offset_item = QtWidgets.QTableWidgetItem("auto")
            offset_item.setFlags(offset_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            w.trace_table.setItem(row, 4, offset_item)

        w.trace_table.resizeColumnsToContents()
        w._updating_trace_table = False

    def trace_table_changed(self, row: int, column: int):
        w = self.window

        if w._updating_trace_table:
            return

        if not (0 <= row < len(w.traces)):
            return

        show_item = w.trace_table.item(row, 0)
        label_item = w.trace_table.item(row, 1)

        if show_item is not None:
            w.traces[row]["visible"] = (
                show_item.checkState() == QtCore.Qt.CheckState.Checked
            )

        if label_item is not None:
            w.traces[row]["label"] = (
                label_item.text().strip() or w.traces[row].get("label", "")
            )

        w.redraw_current_plot()

    def reset_plot(self):
        w = self.window

        w.plot_widget.clear()
        w._marker_lines = []
        w._roi_items = []

        try:
            if w.plot_widget.plotItem.legend is not None:
                w.plot_widget.plotItem.legend.clear()
        except Exception:
            pass

        if w.show_legend_cb.isChecked() and w.plot_widget.plotItem.legend is None:
            w.legend = w.plot_widget.addLegend(offset=(10, 10))
        elif w.show_legend_cb.isChecked():
            w.legend = w.plot_widget.plotItem.legend

        w.plot_widget.addItem(w.vline, ignoreBounds=True)
        w.plot_widget.addItem(w.hline, ignoreBounds=True)

    def pen_for_trace(self, trace: dict, index: int, clean: bool = False):
        role = str(trace.get("role", "")).lower()

        if clean:
            if role == "raw":
                return pg.mkPen((170, 170, 170), width=1.1)

            if role == "baseline":
                return pg.mkPen(
                    (120, 120, 120),
                    width=1.2,
                    style=QtCore.Qt.PenStyle.DashLine,
                )

            return pg.mkPen((0, 0, 0), width=2.2)

        if role == "raw":
            return pg.mkPen((150, 150, 150), width=1.1)

        if role == "baseline":
            return pg.mkPen(
                (120, 120, 120),
                width=1.2,
                style=QtCore.Qt.PenStyle.DashLine,
            )

        return pg.mkPen(pg.intColor(trace.get("color_index", index)), width=1.7)

    def redraw_current_plot(self):
        w = self.window

        self.reset_plot()

        xlim = w._xlim()
        clean = w._clean_figure_mode()

        w.vline.setVisible(not clean)
        w.hline.setVisible(not clean)

        if clean:
            w.plot_widget.showGrid(x=False, y=False)
        else:
            w.plot_widget.showGrid(
                x=w.show_grid_cb.isChecked(),
                y=w.show_grid_cb.isChecked(),
            )

        w.plot_widget.setLabel("bottom", "Raman Shift (cm⁻¹)")

        visible_traces = [tr for tr in w.traces if tr.get("visible", True)]

        if clean:
            clean_traces = [
                tr for tr in visible_traces
                if str(tr.get("role", "")).lower() not in ("raw", "baseline")
            ]

            if clean_traces:
                visible_traces = clean_traces

        if not visible_traces:
            w._draw_region_markers()
            w._draw_peak_markers([])
            w._refresh_peak_table()
            w._refresh_peak_intensity_table()
            w._refresh_roi_table()
            w.plot_widget.setXRange(xlim[0], xlim[1], padding=0)
            return

        mode = w.current_plot_mode

        if mode == "single":
            mode = "overlay"

        left_axis = w.plot_widget.getAxis("left")

        if mode == "overlay":
            try:
                left_axis.setTicks(None)
            except Exception:
                pass

            ylabel = w._axis_y_label(visible_traces[0]["spec"])
            w.plot_widget.setLabel("left", ylabel)

            for i, tr in enumerate(visible_traces):
                x, y = trace_xy(tr)

                show_name = (
                    w.show_legend_cb.isChecked()
                    and not (clean and len(visible_traces) == 1)
                )

                w.plot_widget.plot(
                    x,
                    y,
                    pen=self.pen_for_trace(tr, i, clean=clean),
                    name=tr.get("label", f"Trace {i + 1}") if show_name else None,
                )

        else:
            offset = w._stack_offset_value_from_traces(visible_traces)
            yticks = []

            for i, tr in enumerate(visible_traces):
                x, y = trace_xy(tr)
                y_offset = i * offset

                w.plot_widget.plot(
                    x,
                    y + y_offset,
                    pen=pg.mkPen(
                        pg.intColor(tr.get("color_index", i)),
                        width=1.8,
                    ),
                    name=(
                        tr.get("label", f"Trace {i + 1}")
                        if w.show_legend_cb.isChecked()
                        else None
                    ),
                )

                yticks.append((y_offset, tr.get("label", f"Trace {i + 1}")))

                offset_item = w.trace_table.item(i, 4)
                if offset_item is not None:
                    offset_item.setText(f"{y_offset:.3g}")

            try:
                left_axis.setTicks([yticks])
            except Exception:
                pass

            base_ylabel = w._axis_y_label(visible_traces[0]["spec"])

            if mode == "reference_subtracted_stacked":
                w.plot_widget.setLabel(
                    "left",
                    f"Reference-subtracted {base_ylabel} + offset",
                )
            else:
                w.plot_widget.setLabel("left", f"{base_ylabel} + offset")

        if not clean:
            w._draw_region_markers()
            w._draw_peak_markers(visible_traces)

        w._refresh_peak_table()
        w._refresh_peak_intensity_table()
        w._refresh_roi_table()

        w.plot_widget.setXRange(xlim[0], xlim[1], padding=0)

        if clean:
            ylim = w._robust_ylim_for_traces(visible_traces, xlim)

            if ylim is not None:
                w.plot_widget.setYRange(ylim[0], ylim[1], padding=0)

    def reset_plot_view(self):
        w = self.window

        if w.current_plot_mode == "paax":
            w.plot_widget.enableAutoRange(axis="x", enable=True)
            w.plot_widget.enableAutoRange(axis="y", enable=True)
            w.status_label.setText("EC trace view autoscaled.")
            return

        xmin, xmax = w._xlim()
        w.plot_widget.setXRange(xmin, xmax, padding=0)
        w.plot_widget.enableAutoRange(axis="y", enable=True)
        w.status_label.setText("Plot view reset.")

    def autoscale_y(self):
        w = self.window
        w.plot_widget.enableAutoRange(axis="y", enable=True)
        w.status_label.setText("Y-axis autoscaled.")

    def copy_plot_image(self):
        w = self.window
        pixmap = w.plot_widget.grab()
        QtWidgets.QApplication.clipboard().setPixmap(pixmap)
        w.status_label.setText("Plot image copied to clipboard.")

    def save_plot_png(self):
        w = self.window

        out_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            w,
            "Save plot image",
            "ec_sers_plot.png",
            "PNG files (*.png);;All files (*.*)",
        )

        if not out_path:
            return

        if not out_path.lower().endswith(".png"):
            out_path += ".png"

        pixmap = w.plot_widget.grab()

        if not pixmap.save(out_path):
            QtWidgets.QMessageBox.critical(
                w,
                "Save failed",
                "Could not save plot image.",
            )
            return

        w.status_label.setText(f"Saved plot image: {out_path}")

    def toggle_focus_plot(self, enabled: bool):
        w = self.window

        if hasattr(w, "controls_panel"):
            w.controls_panel.setVisible(not enabled)

        if hasattr(w, "analysis_tabs"):
            if enabled:
                w.analysis_tabs.setVisible(False)
            else:
                show_analysis = True

                if hasattr(w, "show_analysis_panel_cb"):
                    show_analysis = w.show_analysis_panel_cb.isChecked()

                w.analysis_tabs.setVisible(show_analysis)

        if enabled:
            w.focus_plot_btn.setText("Exit Focus")
            w.status_label.setText("Focus plot mode enabled.")
        else:
            w.focus_plot_btn.setText("Focus Plot")
            w.status_label.setText("Focus plot mode disabled.")

    def plot_style_changed(self):
        w = self.window

        if w.current_plot_mode == "paax":
            w.plot_widget.showGrid(
                x=w.show_grid_cb.isChecked(),
                y=w.show_grid_cb.isChecked(),
            )
            return

        w.redraw_current_plot()