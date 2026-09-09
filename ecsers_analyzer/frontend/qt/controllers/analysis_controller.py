from __future__ import annotations

import csv

from PySide6 import QtCore, QtWidgets

from ecsers_analyzer.plotting.roi_regions import (
    VALID_ROI_ROLES,
    clean_roi_role,
    parse_roi_limits,
    roi_default_label,
    should_auto_update_roi_label,
)


class AnalysisController:
    """Qt controller for peak/ROI analysis tables and user actions.

    This controller owns frontend table/dialog/copy/export coordination only.
    Low-level PyQtGraph marker drawing and drag callbacks stay on the main
    window for now.
    """

    def __init__(self, window):
        self.window = window

    # ------------------------------------------------------------------
    # ROI table and actions
    # ------------------------------------------------------------------

    def refresh_roi_table(self):
        """Refresh ROI table from window.region_markers."""
        w = self.window

        if not hasattr(w, "roi_table"):
            return

        w._updating_roi_table = True
        w.roi_table.setRowCount(len(w.region_markers))

        for row, region in enumerate(w.region_markers):
            show_item = QtWidgets.QTableWidgetItem("")
            show_item.setFlags(
                QtCore.Qt.ItemFlag.ItemIsEnabled
                | QtCore.Qt.ItemFlag.ItemIsUserCheckable
                | QtCore.Qt.ItemFlag.ItemIsSelectable
            )
            show_item.setCheckState(
                QtCore.Qt.CheckState.Checked
                if region.visible
                else QtCore.Qt.CheckState.Unchecked
            )
            w.roi_table.setItem(row, 0, show_item)

            label_item = QtWidgets.QTableWidgetItem(region.label)
            label_item.setFlags(label_item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
            w.roi_table.setItem(row, 1, label_item)

            role_item = QtWidgets.QComboBox()
            role_item.addItems(VALID_ROI_ROLES)
            role_item.setCurrentText(region.role)
            role_item.currentTextChanged.connect(
                lambda text, r=row: w._roi_role_changed(r, text)
            )
            w.roi_table.setCellWidget(row, 2, role_item)

            xmin_item = QtWidgets.QTableWidgetItem(f"{region.xmin:.2f}")
            xmin_item.setFlags(xmin_item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
            w.roi_table.setItem(row, 3, xmin_item)

            xmax_item = QtWidgets.QTableWidgetItem(f"{region.xmax:.2f}")
            xmax_item.setFlags(xmax_item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
            w.roi_table.setItem(row, 4, xmax_item)

            width = abs(region.xmax - region.xmin)
            width_item = QtWidgets.QTableWidgetItem(f"{width:.2f}")
            width_item.setFlags(width_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            w.roi_table.setItem(row, 5, width_item)

        w.roi_table.resizeColumnsToContents()
        w._updating_roi_table = False

    def roi_role_changed(self, row: int, role: str):
        """Update ROI role from combo box."""
        w = self.window

        if w._updating_roi_table:
            return

        if not (0 <= row < len(w.region_markers)):
            return

        region = w.region_markers[row]
        old_label = region.label
        region.role = clean_roi_role(role)

        if should_auto_update_roi_label(old_label, region.role):
            region.label = roi_default_label(region.role, region.xmin, region.xmax)

        w.redraw_current_plot()

    def roi_table_changed(self, row: int, column: int):
        """Respond when ROI table values are edited."""
        w = self.window

        if w._updating_roi_table:
            return

        if not (0 <= row < len(w.region_markers)):
            return

        region = w.region_markers[row]

        show_item = w.roi_table.item(row, 0)
        label_item = w.roi_table.item(row, 1)
        xmin_item = w.roi_table.item(row, 3)
        xmax_item = w.roi_table.item(row, 4)

        if column == 0 and show_item is not None:
            region.visible = show_item.checkState() == QtCore.Qt.CheckState.Checked
            w.redraw_current_plot()
            return

        if column == 1 and label_item is not None:
            new_label = label_item.text().strip()
            if new_label:
                region.label = new_label
            w.redraw_current_plot()
            return

        if column in (3, 4):
            try:
                limits = parse_roi_limits(
                    xmin_item.text(),
                    xmax_item.text(),
                )
            except ValueError as exc:
                QtWidgets.QMessageBox.warning(
                    w,
                    "Invalid ROI",
                    str(exc),
                )
                w._refresh_roi_table()
                return

            region.xmin = limits.xmin
            region.xmax = limits.xmax

            if should_auto_update_roi_label(region.label, region.role):
                region.label = roi_default_label(
                    region.role,
                    region.xmin,
                    region.xmax,
                )

            w._refresh_roi_table()
            w.redraw_current_plot()

    def add_roi_from_view(self):
        """Add an ROI using the currently visible x-range."""
        w = self.window
        xmin, xmax = w.plot_widget.viewRange()[0]
        w._add_region_marker(xmin, xmax, role="peak")

    def add_roi_manual(self):
        """Add an ROI using manually entered min/max values."""
        w = self.window

        xmin, ok1 = QtWidgets.QInputDialog.getDouble(
            w,
            "Add ROI",
            "ROI minimum Raman shift (cm⁻¹):",
            1550.0,
            -100000.0,
            100000.0,
            2,
        )
        if not ok1:
            return

        xmax, ok2 = QtWidgets.QInputDialog.getDouble(
            w,
            "Add ROI",
            "ROI maximum Raman shift (cm⁻¹):",
            1650.0,
            -100000.0,
            100000.0,
            2,
        )
        if not ok2:
            return

        w._add_region_marker(xmin, xmax, role="peak")

    def clear_region_markers(self):
        """Remove all ROI region markers."""
        w = self.window
        w.region_markers.clear()
        w._refresh_roi_table()
        w.redraw_current_plot()
        w.status_label.setText("Cleared all ROIs.")

    # ------------------------------------------------------------------
    # Peak marker tables and actions
    # ------------------------------------------------------------------

    def refresh_peak_table(self):
        """Update peak marker table from window.peak_markers."""
        w = self.window

        if not hasattr(w, "peak_table"):
            return

        w._updating_peak_table = True

        visible_traces = [tr for tr in w.traces if tr.get("visible", True)]

        w.peak_table.setRowCount(len(w.peak_markers))

        for row, marker in enumerate(w.peak_markers):
            show_item = QtWidgets.QTableWidgetItem("")
            show_item.setFlags(
                QtCore.Qt.ItemFlag.ItemIsEnabled
                | QtCore.Qt.ItemFlag.ItemIsUserCheckable
                | QtCore.Qt.ItemFlag.ItemIsSelectable
            )
            show_item.setCheckState(
                QtCore.Qt.CheckState.Checked
                if marker.visible
                else QtCore.Qt.CheckState.Unchecked
            )
            w.peak_table.setItem(row, 0, show_item)

            label_item = QtWidgets.QTableWidgetItem(marker.label)
            label_item.setFlags(label_item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
            w.peak_table.setItem(row, 1, label_item)

            x_item = QtWidgets.QTableWidgetItem(f"{marker.x:.2f}")
            x_item.setFlags(x_item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
            w.peak_table.setItem(row, 2, x_item)

            intensity_text = w._peak_intensity_summary(marker.x, visible_traces)
            intensity_item = QtWidgets.QTableWidgetItem(intensity_text)
            intensity_item.setFlags(intensity_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            w.peak_table.setItem(row, 3, intensity_item)

        w.peak_table.resizeColumnsToContents()
        w._updating_peak_table = False

    def peak_table_changed(self, row: int, column: int):
        """Respond when peak marker table is edited."""
        w = self.window

        if w._updating_peak_table:
            return

        if not (0 <= row < len(w.peak_markers)):
            return

        marker = w.peak_markers[row]

        show_item = w.peak_table.item(row, 0)
        label_item = w.peak_table.item(row, 1)
        x_item = w.peak_table.item(row, 2)

        if column == 0 and show_item is not None:
            marker.visible = show_item.checkState() == QtCore.Qt.CheckState.Checked
            w.redraw_current_plot()
            return

        if column == 1 and label_item is not None:
            new_label = label_item.text().strip()
            if new_label:
                marker.label = new_label
            w.redraw_current_plot()
            return

        if column == 2 and x_item is not None:
            try:
                marker.x = float(x_item.text())
            except Exception:
                QtWidgets.QMessageBox.warning(
                    w,
                    "Invalid Raman shift",
                    "Peak marker position must be a number.",
                )
                w._refresh_peak_table()
                return

            if not marker.label.strip() or str(marker.label).endswith("cm⁻¹"):
                marker.label = f"{marker.x:.1f} cm⁻¹"

            w._refresh_peak_table()
            w.redraw_current_plot()
            return

    def refresh_peak_intensity_table(self):
        """Refresh the peak intensity analysis table."""
        w = self.window

        if not hasattr(w, "peak_intensity_table"):
            return

        headers, rows = w._peak_intensity_matrix()

        w.peak_intensity_table.clear()
        w.peak_intensity_table.setColumnCount(len(headers))
        w.peak_intensity_table.setRowCount(len(rows))
        w.peak_intensity_table.setHorizontalHeaderLabels(headers)

        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                if isinstance(value, float):
                    text = f"{value:.6g}"
                else:
                    text = str(value)

                item = QtWidgets.QTableWidgetItem(text)
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                w.peak_intensity_table.setItem(r, c, item)

        w.peak_intensity_table.resizeColumnsToContents()

    def copy_peak_intensity_table(self):
        """Copy peak intensity table as tab-separated text."""
        w = self.window
        headers, rows = w._peak_intensity_matrix()

        lines = ["\t".join(headers)]

        for row in rows:
            out = []
            for value in row:
                if isinstance(value, float):
                    out.append(f"{value:.8g}")
                else:
                    out.append(str(value))
            lines.append("\t".join(out))

        text = "\n".join(lines)

        QtWidgets.QApplication.clipboard().setText(text)
        w.status_label.setText("Peak intensity table copied to clipboard.")

    def export_peak_intensity_csv(self):
        """Export peak intensity table to CSV."""
        w = self.window
        headers, rows = w._peak_intensity_matrix()

        if not rows:
            QtWidgets.QMessageBox.information(
                w,
                "No peak table",
                "There are no visible traces to export.",
            )
            return

        out_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            w,
            "Export peak intensity table",
            "peak_intensity_table.csv",
            "CSV files (*.csv);;All files (*.*)",
        )

        if not out_path:
            return

        try:
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(rows)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                w,
                "Export failed",
                str(exc),
            )
            return

        w.status_label.setText(f"Exported peak intensity table: {out_path}")

    def add_peak_marker_at_cursor(self):
        """Add a peak marker at the current cursor position."""
        w = self.window

        if w.last_cursor_x is None:
            QtWidgets.QMessageBox.information(
                w,
                "No cursor position",
                "Move the mouse over the plot first, then click Add peak marker at cursor.",
            )
            return

        w._add_peak_marker(float(w.last_cursor_x))

    def add_peak_marker_manual(self):
        """Add a peak marker from a manually entered Raman shift."""
        w = self.window

        x, ok = QtWidgets.QInputDialog.getDouble(
            w,
            "Add Peak Marker",
            "Raman shift (cm⁻¹):",
            1590.0,
            -100000.0,
            100000.0,
            2,
        )

        if not ok:
            return

        w._add_peak_marker(float(x))

    def clear_peak_markers(self):
        """Remove all peak markers."""
        w = self.window
        w.peak_markers.clear()
        w._refresh_peak_table()
        w.redraw_current_plot()
        w.status_label.setText("Cleared peak markers.")
