from __future__ import annotations

import sys
from pathlib import Path
from dataclasses import dataclass

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets

from ecsers_analyzer.domain.recipe import ProcessingRecipe
from ecsers_analyzer.services.import_service import ImportService
from ecsers_analyzer.domain.spectrum import Spectrum
from ecsers_analyzer.services.history_service import HistoryService
from ecsers_analyzer.services.export_service import ExportService
from ecsers_analyzer.services.paax_service import PaaxService
from ecsers_analyzer.frontend.qt.tabs.single_tab import build_single_tab as build_single_tab_ui
from ecsers_analyzer.frontend.qt.tabs.ec_tab import build_ec_tab as build_ec_tab_ui
from ecsers_analyzer.frontend.qt.tabs.processing_tab import build_processing_tab as build_processing_tab_ui
from ecsers_analyzer.frontend.qt.tabs.batch_tab import build_batch_tab as build_batch_tab_ui
from ecsers_analyzer.frontend.qt.tabs.plot_tab import build_plot_tab as build_plot_tab_ui
from ecsers_analyzer.frontend.qt.tabs.export_tab import build_export_tab as build_export_tab_ui
from ecsers_analyzer.frontend.qt.tabs.library_tab import build_library_tab as build_library_tab_ui

from ecsers_analyzer.plotting.trace_builder import (
    axis_y_label_for_spec,
    build_batch_traces,
    build_single_traces,
    make_trace,
    stack_offset_value,
    stack_offset_value_from_traces,
    trace_xy,
)
from ecsers_analyzer.export.plan import (
    batch_export_mode,
    batch_mode_needs_stack_offset,
    current_batch_export_labels,
    default_batch_raman_export_filename,
    default_paax_export_filename,
    default_single_raman_export_filename,
    ensure_file_extension,
    normalize_chart_title_mode,
    optional_text,
    overlay_title_for_batch,
    per_sheet_titles_from_specs,
    reference_subtraction_export_warning_needed,
)

from ecsers_analyzer.processing.advisor_workflow import (
    advisor_log_notes,
    advisor_status_applied,
    advisor_status_rejected,
    can_run_advisor,
    recommendation_dialog_message,
    recipe_ui_values,
)

from ecsers_analyzer.services.library_service import LibraryService
from ecsers_analyzer.services.processing_service import ProcessingService
from ecsers_analyzer.processing.form import ProcessingFormValues

from ecsers_analyzer.plotting.peak_analysis import (
    nearest_y_for_trace,
    peak_intensity_matrix,
    peak_intensity_summary,
    peak_value_for_trace,
    robust_ylim_for_traces,
    safe_peak_window_cm1,
)
from ecsers_analyzer.plotting.roi_regions import (
    VALID_ROI_ROLES,
    normalize_roi_limits,
    parse_roi_limits,
    roi_default_label,
    should_auto_update_roi_label,
)
from ecsers_analyzer.frontend.qt.controllers.plot_controller import PlotController
from ecsers_analyzer.frontend.qt.controllers.analysis_controller import AnalysisController

@dataclass
class PeakMarker:
    x: float
    label: str = ""
    visible: bool = True
@dataclass
class RegionMarker:
    xmin: float
    xmax: float
    label: str = ""
    role: str = "peak"
    visible: bool = True
class SpectralViewer(QtWidgets.QMainWindow):
    """Interactive EC-SERS viewer prototype using PySide6 + PyQtGraph.

    Design goal:
    - The plot is a live workspace, not just a button output.
    - The trace table controls visibility and labels.
    - Visual-only changes such as x range and stack offset redraw immediately.
    - Processing/ref subtraction still uses explicit buttons so results remain reproducible.
    """

    # SpectralViewer is intentionally a workflow coordinator.
    # Heavy backend work belongs in ecsers_analyzer/services/.
    # Widget construction belongs in ecsers_analyzer/frontend/qt/tabs/.
    # Qt/PyQtGraph view coordination belongs in ecsers_analyzer/frontend/qt/controllers/.

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def __init__(self):
        super().__init__()

        self.setWindowTitle("EC-SERS Analyzer Qt Prototype")
        self.resize(1450, 850)

        self._init_state()
        self._init_services()
        self._build_ui()
        self._init_controllers()

    def _init_state(self):
        """Initialize mutable application state.

        This method intentionally stores UI/workflow state on the main window.
        Backend services and frontend controllers should operate through this
        shared state instead of duplicating it.
        """
        # Single-spectrum state
        self.raw_spec = None
        self.processed_spec = None
        self.current_path: Path | None = None

        # Electrochemistry / PAAX state
        self.paax_path: Path | None = None
        self.paax_traces = []
        self.paax_visible_traces = []
        self.current_paax_trace = None

        # Batch state
        self.batch_folder: Path | None = None
        self.batch_files: list[Path] = []
        self.batch_files_processed: list[Path] = []
        self.batch_specs = []
        self.batch_labels: list[str] = []
        self.batch_data_are_reference_subtracted = False

        # Plot/trace state
        self.traces: list[dict] = []
        self.current_plot_mode = "single"
        self._updating_trace_table = False

        # Peak/ROI state
        self.peak_markers: list[PeakMarker] = []
        self._updating_peak_table = False
        self.last_cursor_x: float | None = None
        self.last_cursor_y: float | None = None
        self.peak_pick_mode = False
        self._marker_lines: list[pg.InfiniteLine] = []
        self.region_markers: list[RegionMarker] = []
        self._roi_items: list[pg.LinearRegionItem] = []
        self._updating_roi_table = False

    def _init_services(self):
        """Create backend workflow services.

        Services are Qt-free boundaries around import, processing, export,
        library search, PAAX trace planning, and user-history logging.
        """
        self.history_service = HistoryService()
        self.import_service = ImportService()
        self.library_service = LibraryService(history_service=self.history_service)
        self.processing_service = ProcessingService()
        self.export_service = ExportService(history_service=self.history_service)
        self.paax_service = PaaxService()

    def _init_controllers(self):
        """Create frontend controllers after widgets have been built."""
        self.plot_controller = PlotController(self)
        self.analysis_controller = AnalysisController(self)


    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        outer = QtWidgets.QHBoxLayout(central)

        self.main_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        outer.addWidget(self.main_splitter)

        # ---------------- left side: tabbed controls ----------------
        controls = QtWidgets.QFrame()
        controls.setMinimumWidth(360)
        controls.setMaximumWidth(430)
        controls_layout = QtWidgets.QVBoxLayout(controls)

        self.tabs = QtWidgets.QTabWidget()
        controls_layout.addWidget(self.tabs)

        self._build_single_tab()
        self._build_ec_tab()
        self._build_processing_tab()
        self._build_batch_tab()
        self._build_plot_tab()
        self._build_export_tab()
        self._build_library_tab()

        self.status_label = QtWidgets.QLabel("Ready.")
        self.status_label.setWordWrap(True)
        controls_layout.addWidget(self.status_label)

        # ---------------- right side: plot + trace table ----------------
        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setContentsMargins(4, 4, 4, 4)

        right_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        right_layout.addWidget(right_splitter)

        plot_panel = QtWidgets.QWidget()
        plot_layout = QtWidgets.QVBoxLayout(plot_panel)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        self.plot_toolbar = QtWidgets.QFrame()
        toolbar_layout = QtWidgets.QHBoxLayout(self.plot_toolbar)
        toolbar_layout.setContentsMargins(2, 2, 2, 2)

        self.reset_view_btn = QtWidgets.QPushButton("Reset View")
        self.reset_view_btn.clicked.connect(self.reset_plot_view)
        toolbar_layout.addWidget(self.reset_view_btn)

        self.auto_y_btn = QtWidgets.QPushButton("Auto Y")
        self.auto_y_btn.clicked.connect(self.autoscale_y)
        toolbar_layout.addWidget(self.auto_y_btn)

        toolbar_layout.addSpacing(12)
        self.add_roi_view_btn = QtWidgets.QPushButton("Add ROI from View")
        self.add_roi_view_btn.clicked.connect(self.add_roi_from_view)
        toolbar_layout.addWidget(self.add_roi_view_btn)

        self.add_roi_manual_btn = QtWidgets.QPushButton("Add ROI Manual")
        self.add_roi_manual_btn.clicked.connect(self.add_roi_manual)
        toolbar_layout.addWidget(self.add_roi_manual_btn)

        self.clear_rois_btn = QtWidgets.QPushButton("Clear ROIs")
        self.clear_rois_btn.clicked.connect(self.clear_region_markers)
        toolbar_layout.addWidget(self.clear_rois_btn)

        toolbar_layout.addSpacing(12)

        self.pick_peak_btn = QtWidgets.QPushButton("Pick Peak")
        self.pick_peak_btn.setCheckable(True)
        self.pick_peak_btn.toggled.connect(self._set_peak_pick_mode)
        toolbar_layout.addWidget(self.pick_peak_btn)

        self.add_peak_manual_toolbar_btn = QtWidgets.QPushButton("Add Peak by cm⁻¹")
        self.add_peak_manual_toolbar_btn.clicked.connect(self.add_peak_marker_manual)
        toolbar_layout.addWidget(self.add_peak_manual_toolbar_btn)

        self.clear_peaks_toolbar_btn = QtWidgets.QPushButton("Clear Peaks")
        self.clear_peaks_toolbar_btn.clicked.connect(self.clear_peak_markers)
        toolbar_layout.addWidget(self.clear_peaks_toolbar_btn)

        toolbar_layout.addSpacing(12)

        self.copy_plot_btn = QtWidgets.QPushButton("Copy Plot")
        self.copy_plot_btn.clicked.connect(self.copy_plot_image)
        toolbar_layout.addWidget(self.copy_plot_btn)

        self.save_plot_btn = QtWidgets.QPushButton("Save PNG")
        self.save_plot_btn.clicked.connect(self.save_plot_png)
        toolbar_layout.addWidget(self.save_plot_btn)

        toolbar_layout.addSpacing(12)

        self.focus_plot_btn = QtWidgets.QPushButton("Focus Plot")
        self.focus_plot_btn.setCheckable(True)
        self.focus_plot_btn.toggled.connect(self._toggle_focus_plot)
        toolbar_layout.addWidget(self.focus_plot_btn)

        toolbar_layout.addStretch()

        plot_layout.addWidget(self.plot_toolbar)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("w")
        self.plot_widget.showGrid(x=False, y=False)
        self.plot_widget.setLabel("bottom", "Raman Shift (cm⁻¹)")
        self.plot_widget.setLabel("left", "Intensity (a.u.)")
        self.plot_widget.getAxis("bottom").enableAutoSIPrefix(False)
        self.plot_widget.getAxis("left").enableAutoSIPrefix(False)
        self.plot_widget.setXRange(400, 1700, padding=0)
        self.legend = self.plot_widget.addLegend(offset=(10, 10))

        # Crosshair
        self.vline = pg.InfiniteLine(angle=90, movable=False)
        self.hline = pg.InfiniteLine(angle=0, movable=False)
        self.plot_widget.addItem(self.vline, ignoreBounds=True)
        self.plot_widget.addItem(self.hline, ignoreBounds=True)

        self.proxy = pg.SignalProxy(
            self.plot_widget.scene().sigMouseMoved,
            rateLimit=60,
            slot=self._mouse_moved,
        )
        self.plot_widget.scene().sigMouseClicked.connect(self._plot_mouse_clicked)

        plot_layout.addWidget(self.plot_widget, stretch=1)

        bottom_bar = QtWidgets.QHBoxLayout()
        self.cursor_label = QtWidgets.QLabel("Cursor: —")
        self.nearest_label = QtWidgets.QLabel("Nearest: —")
        bottom_bar.addWidget(self.cursor_label)
        bottom_bar.addWidget(self.nearest_label)
        bottom_bar.addStretch()
        plot_layout.addLayout(bottom_bar)
        right_splitter.addWidget(plot_panel)

        self.analysis_tabs = QtWidgets.QTabWidget()
        self.analysis_tabs.setDocumentMode(True)
        right_splitter.addWidget(self.analysis_tabs)
        trace_box = QtWidgets.QGroupBox("Trace Table")
        trace_layout = QtWidgets.QVBoxLayout(trace_box)
        self.trace_table = QtWidgets.QTableWidget(0, 5)
        self.trace_table.setHorizontalHeaderLabels(["Show", "Label", "Role", "File", "Offset"])
        self.trace_table.horizontalHeader().setStretchLastSection(True)
        self.trace_table.verticalHeader().setVisible(False)
        self.trace_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.trace_table.setMinimumHeight(170)
        self.trace_table.cellChanged.connect(self._trace_table_changed)
        trace_layout.addWidget(self.trace_table)
        self.analysis_tabs.addTab(trace_box, "Traces")
        peak_box = QtWidgets.QGroupBox("Peak Marker Table")
        peak_layout = QtWidgets.QVBoxLayout(peak_box)

        self.peak_table = QtWidgets.QTableWidget(0, 4)
        self.peak_table.setHorizontalHeaderLabels([
            "Show",
            "Label",
            "cm⁻¹",
            "Visible trace intensities",
        ])
        self.peak_table.horizontalHeader().setStretchLastSection(True)
        self.peak_table.verticalHeader().setVisible(False)
        self.peak_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.peak_table.setMinimumHeight(120)
        self.peak_table.setMaximumHeight(180)
        self.peak_table.cellChanged.connect(self._peak_table_changed)

        peak_layout.addWidget(self.peak_table)
        self.analysis_tabs.addTab(peak_box, "Peak markers")
        intensity_box = QtWidgets.QGroupBox("Peak Intensity Analysis Table")
        intensity_layout = QtWidgets.QVBoxLayout(intensity_box)

        intensity_controls = QtWidgets.QHBoxLayout()

        self.peak_intensity_method_combo = QtWidgets.QComboBox()
        self.peak_intensity_method_combo.addItems([
            "nearest",
            "local_max_window",
        ])
        self.peak_intensity_method_combo.currentTextChanged.connect(
            lambda *_: self._refresh_peak_intensity_table()
        )
        intensity_controls.addWidget(QtWidgets.QLabel("Method:"))
        intensity_controls.addWidget(self.peak_intensity_method_combo)

        self.peak_window_edit = QtWidgets.QLineEdit("5")
        self.peak_window_edit.setMaximumWidth(70)
        self.peak_window_edit.editingFinished.connect(self._refresh_peak_intensity_table)
        intensity_controls.addWidget(QtWidgets.QLabel("Window ±cm⁻¹:"))
        intensity_controls.addWidget(self.peak_window_edit)

        self.copy_peak_intensity_btn = QtWidgets.QPushButton("Copy")
        self.copy_peak_intensity_btn.clicked.connect(self.copy_peak_intensity_table)
        intensity_controls.addWidget(self.copy_peak_intensity_btn)

        self.export_peak_intensity_btn = QtWidgets.QPushButton("Export CSV")
        self.export_peak_intensity_btn.clicked.connect(self.export_peak_intensity_csv)
        intensity_controls.addWidget(self.export_peak_intensity_btn)

        intensity_controls.addStretch()
        intensity_layout.addLayout(intensity_controls)

        self.peak_intensity_table = QtWidgets.QTableWidget(0, 0)
        self.peak_intensity_table.horizontalHeader().setStretchLastSection(True)
        self.peak_intensity_table.verticalHeader().setVisible(False)
        self.peak_intensity_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.peak_intensity_table.setMinimumHeight(160)
        self.peak_intensity_table.setAlternatingRowColors(True)

        intensity_layout.addWidget(self.peak_intensity_table)

        self.analysis_tabs.addTab(intensity_box, "Peak analysis")
        roi_box = QtWidgets.QGroupBox("ROI / Region Table")
        roi_layout = QtWidgets.QVBoxLayout(roi_box)

        roi_help = QtWidgets.QLabel(
            "Use ROIs for peak regions, noise regions, normalization ranges, "
            "baseline exclusions, or integration windows."
        )
        roi_help.setWordWrap(True)
        roi_layout.addWidget(roi_help)

        self.roi_table = QtWidgets.QTableWidget(0, 6)
        self.roi_table.setHorizontalHeaderLabels([
            "Show",
            "Label",
            "Role",
            "Min cm⁻¹",
            "Max cm⁻¹",
            "Width",
        ])
        self.roi_table.horizontalHeader().setStretchLastSection(True)
        self.roi_table.verticalHeader().setVisible(False)
        self.roi_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.roi_table.setAlternatingRowColors(True)
        self.roi_table.cellChanged.connect(self._roi_table_changed)

        roi_layout.addWidget(self.roi_table)

        self.analysis_tabs.addTab(roi_box, "ROIs")

        right_splitter.setStretchFactor(0, 5)
        right_splitter.setStretchFactor(1, 2)
        right_splitter.setSizes([620, 230])
        
        self.controls_panel = controls

        self.main_splitter.addWidget(controls)
        self.main_splitter.addWidget(right)
        self.main_splitter.setSizes([390, 1060])

    def _build_single_tab(self):
        build_single_tab_ui(self)

    def _build_ec_tab(self):
        build_ec_tab_ui(self)

    def _build_processing_tab(self):
        build_processing_tab_ui(self)

    def _build_batch_tab(self):
        build_batch_tab_ui(self)

    def _build_plot_tab(self):
        build_plot_tab_ui(self)

    def _build_export_tab(self):
        build_export_tab_ui(self)

    def _build_library_tab(self):
        build_library_tab_ui(self)

    def _toggle_analysis_panel(self, *_):
        """Show/hide the bottom analysis tab panel."""
        if not hasattr(self, "analysis_tabs"):
            return

        visible = self.show_analysis_panel_cb.isChecked()
        self.analysis_tabs.setVisible(visible)

        if visible:
            self.status_label.setText("Analysis panel shown.")
        else:
            self.status_label.setText("Analysis panel hidden for focused plotting.")


    # ------------------------------------------------------------------
    # General UI/value helpers
    # ------------------------------------------------------------------

    def _safe_float(self, text: str, default: float) -> float:
        try:
            return float(text)
        except Exception:
            return default

    def _safe_int(self, text: str, default: int) -> int:
        try:
            return int(float(text))
        except Exception:
            return default

    def _xlim(self):
        xmin = self._safe_float(self.xmin_edit.text(), 400.0)
        xmax = self._safe_float(self.xmax_edit.text(), 1700.0)
        return min(xmin, xmax), max(xmin, xmax)

    def _clean_figure_mode(self) -> bool:
        return bool(
            hasattr(self, "clean_figure_cb")
            and self.clean_figure_cb.isChecked()
        )

    def _axis_y_label(self, spec):
        return axis_y_label_for_spec(spec)

    def _export_chart_title_text(self) -> str:
        return self.export_title_text_edit.text().strip()

    def _export_y_axis_label_override(self) -> str | None:
        return optional_text(self.export_y_label_edit.text())

    def _export_chart_title_mode(self) -> str:
        return normalize_chart_title_mode(self.export_title_mode_combo.currentText())


    # ------------------------------------------------------------------
    # Processing and advisor workflow
    # ------------------------------------------------------------------

    def _processing_form_values(self) -> ProcessingFormValues:
        return ProcessingFormValues(
            despike_checked=self.despike_cb.isChecked() if hasattr(self, "despike_cb") else False,
            despike_window=self.despike_window_edit.text() if hasattr(self, "despike_window_edit") else "7",
            despike_threshold=self.despike_threshold_edit.text() if hasattr(self, "despike_threshold_edit") else "7.0",
            despike_max_width_points=self.despike_max_width_edit.text() if hasattr(self, "despike_max_width_edit") else "1",

            baseline=self.baseline_combo.currentText(),
            lam=self.lam_edit.text(),
            max_iter=self.iter_edit.text(),

            smooth_checked=self.smooth_cb.isChecked() if hasattr(self, "smooth_cb") else False,
            smooth_window_points=self.smooth_edit.text(),
            smooth_width_enabled=self.smooth_cm1_cb.isChecked() if hasattr(self, "smooth_cm1_cb") else False,
            smooth_width_cm1=self.smooth_cm1_edit.text() if hasattr(self, "smooth_cm1_edit") else "18",
            smooth_polyorder=self.smooth_poly_edit.text(),

            normalize=self.norm_combo.currentText(),
            laser_power_mw=self.power_edit.text(),
        )

    def _current_processing_recipe(self, raw_spec=None, label: str = "") -> ProcessingRecipe:
        """Read Processing tab controls and return one reproducible recipe."""
        form = self._processing_form_values()

        plan = self.processing_service.build_recipe_from_form(
            form,
            raw_spec=raw_spec,
        )

        if plan.needs_acquisition_time:
            t, ok = QtWidgets.QInputDialog.getDouble(
                self,
                "Acquisition time required",
                f"Acquisition time for {label or 'spectrum'} (s):",
                plan.acquisition_time_default_s,
                0.001,
                100000.0,
                3,
            )

            if not ok:
                raise ValueError("Power-time normalization cancelled.")

            plan = self.processing_service.build_recipe_from_form(
                form,
                raw_spec=raw_spec,
                provided_integration_time_s=float(t),
            )

        if not plan.ok or plan.recipe is None:
            raise ValueError(plan.error_message or "Invalid processing settings.")

        return plan.recipe

    def _active_raw_spectrum_for_advisor(self):
        """Return current raw spectrum for recommendation."""
        if self.raw_spec is not None:
            return self.raw_spec, self.current_path

        files = self._selected_batch_files() if hasattr(self, "_selected_batch_files") else []

        if files:
            p = files[0]
            raw = self._load_any_spectrum(p)
            return raw, p

        return None, None

    def _apply_recipe_to_ui(self, recipe: ProcessingRecipe):
        """Fill Processing tab controls from a ProcessingRecipe."""
        values = recipe_ui_values(recipe)

        self.despike_cb.setChecked(values["despike_checked"])
        self.despike_window_edit.setText(values["despike_window"])
        self.despike_threshold_edit.setText(values["despike_threshold"])
        self.despike_max_width_edit.setText(values["despike_max_width_points"])

        self.baseline_combo.setCurrentText(values["baseline"])

        if values["lam"]:
            self.lam_edit.setText(values["lam"])

        if values["max_iter"]:
            self.iter_edit.setText(values["max_iter"])

        self.smooth_cb.setChecked(values["smooth_checked"])
        self.smooth_edit.setText(values["smooth_window_points"])

        self.smooth_cm1_cb.setChecked(values["smooth_width_enabled"])

        if values["smooth_width_cm1"]:
            self.smooth_cm1_edit.setText(values["smooth_width_cm1"])

        self.smooth_poly_edit.setText(values["smooth_polyorder"])
        self.norm_combo.setCurrentText(values["normalize"])

        if values["laser_power_mw"]:
            self.power_edit.setText(values["laser_power_mw"])

    def recommend_processing_settings(self):
        """Analyze current spectrum and recommend processing settings."""
        raw, path = self._active_raw_spectrum_for_advisor()

        result = self.processing_service.recommend_processing(
            raw_spec=raw,
            purpose="plot",
        )

        if not result.ok:
            if result.error_title == "No spectrum":
                QtWidgets.QMessageBox.information(
                    self,
                    result.error_title,
                    result.error_message,
                )
            else:
                QtWidgets.QMessageBox.critical(
                    self,
                    result.error_title,
                    result.error_message,
                )
            return

        rec = result.recommendation
        recipe = rec.recipe

        answer = QtWidgets.QMessageBox.question(
            self,
            "Processing recommendation",
            recommendation_dialog_message(rec),
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
        )

        if answer == QtWidgets.QMessageBox.StandardButton.Yes:
            self._apply_recipe_to_ui(recipe)

            self.status_label.setText(advisor_status_applied())

            self.history_service.log_advisor_decision(
                decision="accepted",
                source_path=path,
                raw_spec=raw,
                processed_spec=self.processed_spec,
                recipe=recipe,
                notes=advisor_log_notes(rec, decision="accepted"),
            )

        else:
            self.status_label.setText(advisor_status_rejected())

            self.history_service.log_advisor_decision(
                decision="rejected",
                source_path=path,
                raw_spec=raw,
                processed_spec=self.processed_spec,
                recipe=recipe,
                notes=advisor_log_notes(rec, decision="rejected"),
            )

    def _processing_settings_changed(self, *_):
        """Tell the user that already-processed data must be rerun."""
        if self.processed_spec is not None or self.batch_specs:
            self.status_label.setText(
                "Processing settings changed. Click Run Processing or "
                "Run Batch Processing + Plot again to apply the new settings."
            )

    def _process_spectrum_copy(self, raw_spec, label: str = ""):
        """Process one raw Spectrum using the current Processing tab recipe."""
        recipe = self._current_processing_recipe(raw_spec=raw_spec, label=label)

        result = self.processing_service.process_single(
            raw_spec=raw_spec,
            recipe=recipe,
        )

        if not result.ok:
            raise RuntimeError(result.error_message or "Processing failed.")

        return result.processed_spec

    def run_processing(self):
        if self.raw_spec is None:
            QtWidgets.QMessageBox.warning(
                self,
                "No spectrum",
                "Open a CSV or SPE file first.",
            )
            return

        try:
            recipe = self._current_processing_recipe(
                raw_spec=self.raw_spec,
                label=self.current_path.name if self.current_path else "spectrum",
            )

            result = self.processing_service.process_single(
                raw_spec=self.raw_spec,
                recipe=recipe,
            )

            if not result.ok:
                QtWidgets.QMessageBox.critical(
                    self,
                    result.error_title,
                    result.error_message,
                )
                return

            self.processed_spec = result.processed_spec

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Processing failed",
                str(e),
            )
            return

        self.show_processed_cb.setChecked(True)
        self.update_single_traces()

        recipe_md = getattr(self.processed_spec, "processing_recipe", {}) or {}
        n_spikes = getattr(self.processed_spec, "n_spikes_removed", 0)

        self.history_service.log_single_processed(
            source_path=self.current_path,
            raw_spec=self.raw_spec,
            processed_spec=self.processed_spec,
        )

        self.status_label.setText(
            f"Processed {self.current_path.name if self.current_path else ''}\n"
            f"Baseline: {recipe_md.get('baseline', '')}\n"
            f"Despike: {recipe_md.get('despike', False)}, spikes removed: {n_spikes}\n"
            f"Smoothing: {recipe_md.get('smooth_width_cm1', '')} cm⁻¹ "
            f"→ {recipe_md.get('final_smooth_window_points', '')} points\n"
            f"Polyorder: {recipe_md.get('smooth_polyorder', '')}\n"
            f"Normalize: {recipe_md.get('normalize', '')}"
        )


    # ------------------------------------------------------------------
    # Single-spectrum file workflow
    # ------------------------------------------------------------------

    def _discover_spectral_files(self, folder: Path) -> list[Path]:
        return self.import_service.discover_spectral_files(folder)

    def _display_name(self, p: Path) -> str:
        return self.import_service.display_name(
            p,
            base_folder=self.batch_folder,
        )

    def _load_any_spectrum(self, p: Path):
        power = self._safe_float(self.power_edit.text(), 34.1)

        result = self.import_service.load_spectrum_file(
            p,
            laser_power_mw=power,
        )

        if not result.ok:
            raise ValueError(result.error_message)

        return result.spectrum

    def open_spectrum(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open spectrum",
            "",
            "Spectral files (*.csv *.spe);;CSV files (*.csv);;SPE files (*.spe);;All files (*.*)",
        )
        if not path:
            return

        p = Path(path)
        try:
            spec = self._load_any_spectrum(p)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Load failed", str(e))
            return

        self.current_path = p
        self.raw_spec = spec
        self.processed_spec = None
        self.current_plot_mode = "single"

        self.file_label.setText(str(p))
        self.status_label.setText(
            f"Loaded {p.name}\n"
            f"Points: {len(spec.x)}\n"
            f"X range: {float(np.nanmin(spec.x)):.2f}–{float(np.nanmax(spec.x)):.2f} cm⁻¹"
        )
        self.show_raw_cb.setChecked(True)
        self.show_processed_cb.setChecked(False)
        self.update_single_traces()

    def update_single_traces(self):
        file_name = self.current_path.name if self.current_path else ""

        traces = build_single_traces(
            raw_spec=self.raw_spec,
            processed_spec=self.processed_spec,
            file_name=file_name,
            show_raw=self.show_raw_cb.isChecked(),
            show_processed=self.show_processed_cb.isChecked(),
            show_baseline=self.show_baseline_cb.isChecked(),
        )

        self.current_plot_mode = "single"
        self._set_traces(traces)


    # ------------------------------------------------------------------
    # Batch workflow
    # ------------------------------------------------------------------

    def open_batch_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select batch folder", "")
        if not folder:
            return

        self.batch_folder = Path(folder)
        self.batch_files = self._discover_spectral_files(self.batch_folder)
        self.batch_files_processed = []
        self.batch_specs = []
        self.batch_labels = []
        self.batch_data_are_reference_subtracted = False

        self.batch_list.clear()
        self.reference_combo.clear()
        self.bottom_combo.clear()

        for p in self.batch_files:
            name = self._display_name(p)
            self.batch_list.addItem(name)
            self.reference_combo.addItem(name)
            self.bottom_combo.addItem(name)

        for i in range(self.batch_list.count()):
            self.batch_list.item(i).setSelected(True)

        # Prefer -1.0 V as reference if present.
        ref_index = 0
        for i, p in enumerate(self.batch_files):
            n = p.name.lower().replace(" ", "")
            if "-1.0" in n or "-1v" in n or "m1.0" in n or "m1v" in n:
                ref_index = i
                break
        if self.batch_files:
            self.reference_combo.setCurrentIndex(ref_index)

        # Prefer OCP as bottom spectrum if present.
        bottom_index = 0
        for i, p in enumerate(self.batch_files):
            if "ocp" in p.name.lower():
                bottom_index = i
                break
        if self.batch_files:
            self.bottom_combo.setCurrentIndex(bottom_index)

        self.batch_folder_label.setText(str(self.batch_folder))
        self.status_label.setText(f"Found {len(self.batch_files)} spectral file(s).")

    def _selected_batch_files(self) -> list[Path]:
        if not self.batch_files:
            return []
        selected_items = self.batch_list.selectedItems()
        if not selected_items:
            return list(self.batch_files)
        out = []
        for item in selected_items:
            row = self.batch_list.row(item)
            if 0 <= row < len(self.batch_files):
                out.append(self.batch_files[row])
        return out

    def _combo_path(self, combo: QtWidgets.QComboBox) -> Path | None:
        text = combo.currentText().strip()
        if not text:
            return None
        for p in self.batch_files:
            if self._display_name(p) == text or p.name == text:
                return p
        return None

    def _reference_subtracted_raw(self, sample_spec, ref_spec, ref_path: Path):
        sample_x = np.asarray(sample_spec.x_raw, dtype=float)
        sample_y = np.asarray(sample_spec.y_raw, dtype=float)
        ref_x = np.asarray(ref_spec.x_raw, dtype=float)
        ref_y = np.asarray(ref_spec.y_raw, dtype=float)

        if sample_x.size == 0 or ref_x.size == 0:
            raise ValueError("Cannot subtract reference: empty spectrum.")
        if not np.isfinite(sample_x).all() or not np.isfinite(sample_y).all():
            raise ValueError("Sample contains NaN/inf.")
        if not np.isfinite(ref_x).all() or not np.isfinite(ref_y).all():
            raise ValueError("Reference contains NaN/inf.")

        order = np.argsort(ref_x)
        ref_interp = np.interp(sample_x, ref_x[order], ref_y[order])
        corrected_y = sample_y - ref_interp

        md = dict(getattr(sample_spec, "metadata", {}) or {})
        md["background_correction"] = "reference_subtraction"
        md["reference_file"] = ref_path.name
        md["reference_subtraction_stage"] = "raw_before_preprocessing"
        md["reference_interpolation"] = "reference_interpolated_to_sample_x"
        return Spectrum(sample_x.copy(), corrected_y.copy(), metadata=md)

    def _reorder_bottom(self, files, specs, labels):
        bottom_path = self._combo_path(self.bottom_combo)
        if bottom_path is None:
            return files, specs, labels

        bottom_idx = None
        for i, p in enumerate(files):
            try:
                same = p.resolve() == bottom_path.resolve()
            except Exception:
                same = p == bottom_path
            if same:
                bottom_idx = i
                break
        if bottom_idx is None:
            return files, specs, labels

        order = [bottom_idx] + [i for i in range(len(files)) if i != bottom_idx]
        return [files[i] for i in order], [specs[i] for i in order], [labels[i] for i in order]

    def run_batch_plot(self):
        files = self._selected_batch_files()
        if not files:
            QtWidgets.QMessageBox.warning(self, "No files", "Select a folder containing CSV/SPE files first.")
            return

        mode = self.batch_mode_combo.currentText().lower()
        use_reference = mode == "reference_subtracted_stacked"
        ref_path = None
        ref_raw = None

        if use_reference:
            ref_path = self._combo_path(self.reference_combo)
            if ref_path is None:
                QtWidgets.QMessageBox.warning(self, "No reference", "Choose a reference spectrum first.")
                return
            try:
                ref_raw = self._load_any_spectrum(ref_path)
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Reference load failed", str(e))
                return

        processed_files = []
        specs = []
        labels = []

        for p in files:
            try:
                if (
                    use_reference
                    and self.skip_reference_cb.isChecked()
                    and ref_path is not None
                    and p.resolve() == ref_path.resolve()
                ):
                    continue

                raw = self._load_any_spectrum(p)
                if use_reference:
                    raw = self._reference_subtracted_raw(raw, ref_raw, ref_path)

                label = p.stem
                spec = self._process_spectrum_copy(raw, label=label)
                processed_files.append(p)
                specs.append(spec)
                labels.append(label)
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Batch processing failed", f"{p.name}\n\n{e}")
                return

        if not specs:
            QtWidgets.QMessageBox.warning(
                self,
                "No spectra processed",
                "No spectra were processed. Check whether only the reference file was selected and skipped.",
            )
            return

        if mode in ("stacked", "reference_subtracted_stacked"):
            processed_files, specs, labels = self._reorder_bottom(processed_files, specs, labels)

        self.batch_files_processed = processed_files
        self.batch_specs = specs
        self.batch_labels = labels
        self.batch_data_are_reference_subtracted = use_reference
        self.current_plot_mode = mode
        self._set_batch_traces(specs, labels, processed_files, mode)

        for p, spec in zip(processed_files, specs):
            self.history_service.log_batch_processed(
                source_path=p,
                processed_spec=spec,
                notes=f"mode={mode}; reference_subtracted={use_reference}",
            )

        total_spikes = sum(
            int(getattr(s, "n_spikes_removed", 0) or 0)
            for s in specs
        )

        recipe = getattr(specs[0], "processing_recipe", {}) if specs else {}

        self.status_label.setText(
            f"Batch processed: {len(specs)} spectra\n"
            f"Mode: {mode}\n"
            f"Baseline: {recipe.get('baseline', '')}\n"
            f"Despike: {recipe.get('despike', False)}, total spikes removed: {total_spikes}\n"
            f"Smoothing: {recipe.get('smooth_width_cm1', '')} cm⁻¹ "
            f"→ {recipe.get('final_smooth_window_points', '')} points\n"
            f"Polyorder: {recipe.get('smooth_polyorder', '')}\n"
            f"Normalize: {recipe.get('normalize', '')}"
        )

    def _batch_mode_changed(self, *_):
        if not self.batch_specs:
            return
        new_mode = self.batch_mode_combo.currentText().lower()
        if new_mode == "reference_subtracted_stacked" and not self.batch_data_are_reference_subtracted:
            self.status_label.setText("Reference subtraction changes the data. Click Run Batch Plot to apply it.")
            return
        self.current_plot_mode = new_mode
        self.redraw_current_plot()

    def _bottom_changed(self, *_):
        if not self.batch_specs or self.current_plot_mode not in ("stacked", "reference_subtracted_stacked"):
            return
        files, specs, labels = self._reorder_bottom(self.batch_files_processed, self.batch_specs, self.batch_labels)
        self.batch_files_processed = files
        self.batch_specs = specs
        self.batch_labels = labels
        self._set_batch_traces(specs, labels, files, self.current_plot_mode)

    def _set_batch_traces(self, specs, labels, files, mode):
        traces = build_batch_traces(
            specs=specs,
            labels=labels,
            files=files,
            mode=mode,
        )
        self._set_traces(traces)


    # ------------------------------------------------------------------
    # PAAX / electrochemistry workflow
    # ------------------------------------------------------------------

    def _paax_meta(self, trace, key: str, default=""):
        return self.paax_service.trace_meta(trace, key, default)

    def _paax_study_name(self, trace) -> str:
        return self.paax_service.study_name(trace)

    def _paax_trace_name(self, trace) -> str:
        return self.paax_service.trace_name(trace)

    def _paax_x_label(self, trace) -> str:
        return self.paax_service.x_label(trace)

    def _paax_y_label(self, trace) -> str:
        return self.paax_service.y_label(trace)

    def open_paax(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open AfterMath PAAX file",
            "",
            "AfterMath PAAX files (*.paax);;All files (*.*)",
        )

        if not path:
            return

        p = Path(path)

        result = self.import_service.load_paax_file(p)

        if not result.ok:
            if result.error_title == "PAAX import failed":
                QtWidgets.QMessageBox.critical(
                    self,
                    result.error_title,
                    result.error_message,
                )
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    result.error_title,
                    result.error_message,
                )
            return

        traces = result.traces or []

        self.paax_path = p
        self.paax_traces = list(traces)
        self.paax_visible_traces = []
        self.current_paax_trace = None

        plan = self.paax_service.loaded_file_plan(
            path=p,
            traces=self.paax_traces,
        )

        self.paax_study_combo.blockSignals(True)
        self.paax_study_combo.clear()
        self.paax_study_combo.addItems(plan.studies)
        self.paax_study_combo.blockSignals(False)

        if plan.studies:
            self.paax_study_combo.setCurrentIndex(0)

        self.refresh_paax_trace_dropdown()

        self.paax_file_label.setText(plan.file_label)
        self.status_label.setText(plan.status_message)

    def refresh_paax_trace_dropdown(self):
        if not hasattr(self, "paax_trace_combo"):
            return

        study = self.paax_study_combo.currentText().strip()

        self.paax_trace_combo.clear()
        self.paax_visible_traces = []

        if not study or not self.paax_traces:
            return

        plan = self.paax_service.dropdown_plan(
            traces=self.paax_traces,
            selected_study=study,
        )

        self.paax_visible_traces = plan.visible_traces
        self.paax_trace_combo.addItems(plan.dropdown_labels)

    def _selected_paax_trace(self):
        return self.paax_service.selected_trace(
            visible_traces=self.paax_visible_traces,
            selected_index=self.paax_trace_combo.currentIndex(),
        )

    def plot_paax_trace(self):
        trace = self._selected_paax_trace()

        plan = self.paax_service.plot_plan(
            trace=trace,
            source_path=self.paax_path,
            color_index=0,
        )

        if not plan.ok:
            if plan.error_title == "Plot failed":
                QtWidgets.QMessageBox.critical(
                    self,
                    plan.error_title,
                    plan.error_message,
                )
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    plan.error_title,
                    plan.error_message,
                )
            return

        self.current_paax_trace = plan.trace
        self.current_plot_mode = "paax"

        self._reset_plot()

        self.plot_widget.setLabel("bottom", plan.xlabel)
        self.plot_widget.setLabel("left", plan.ylabel)
        self.plot_widget.showGrid(
            x=self.show_grid_cb.isChecked(),
            y=self.show_grid_cb.isChecked(),
        )

        self.plot_widget.plot(
            plan.x,
            plan.y,
            pen=pg.mkPen(pg.intColor(0), width=1.8),
            name=plan.name if self.show_legend_cb.isChecked() else None,
        )

        x_range, y_range = self.paax_service.finite_ranges(plan.x, plan.y)

        if x_range is not None:
            self.plot_widget.setXRange(
                x_range[0],
                x_range[1],
                padding=0.02,
            )

        if y_range is not None:
            self.plot_widget.enableAutoRange(axis="y", enable=True)

        self.traces = [plan.trace_dict]
        self._refresh_trace_table()

        self.status_label.setText(plan.status_message)

    def export_paax_selected_csv(self):
        trace = self._selected_paax_trace()

        if trace is None:
            QtWidgets.QMessageBox.warning(
                self,
                "No PAAX trace",
                "Open a PAAX file and choose a trace first.",
            )
            return

        study = self.paax_service.study_name(trace)
        name = self.paax_service.trace_name(trace)

        default_name = default_paax_export_filename(study, name, ".csv")

        out_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export selected PAAX trace",
            default_name,
            "CSV files (*.csv);;All files (*.*)",
        )

        if not out_path:
            return

        out_path = ensure_file_extension(out_path, ".csv")

        result = self.export_service.export_paax_csv(
            trace=trace,
            out_path=out_path,
        )

        if not result.ok:
            QtWidgets.QMessageBox.critical(
                self,
                result.error_title,
                result.error_message,
            )
            return

        self.status_label.setText(result.status_message)

        QtWidgets.QMessageBox.information(
            self,
            "Export complete",
            f"Saved:\n{result.output_path}",
        )

    def export_paax_selected_excel(self):
        """Export the selected PAAX electrochemistry trace to an Excel workbook."""
        trace = self._selected_paax_trace()

        if trace is None:
            QtWidgets.QMessageBox.warning(
                self,
                "No PAAX trace",
                "Open a PAAX file and choose a trace first.",
            )
            return

        study = self.paax_service.study_name(trace)
        name = self.paax_service.trace_name(trace)

        default_name = default_paax_export_filename(study, name, ".xlsx")

        out_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export selected PAAX trace to Excel",
            default_name,
            "Excel files (*.xlsx);;All files (*.*)",
        )

        if not out_path:
            return

        out_path = ensure_file_extension(out_path, ".xlsx")

        result = self.export_service.export_paax_excel(
            trace=trace,
            out_path=out_path,
            source_path=self.paax_path,
        )

        if not result.ok:
            if result.error_title in ("Missing dependency", "Invalid trace"):
                QtWidgets.QMessageBox.warning(
                    self,
                    result.error_title,
                    result.error_message,
                )
            else:
                QtWidgets.QMessageBox.critical(
                    self,
                    result.error_title,
                    result.error_message,
                )
            return

        self.status_label.setText(result.status_message)

        QtWidgets.QMessageBox.information(
            self,
            "Export complete",
            f"Saved:\n{result.output_path}",
        )


    # ------------------------------------------------------------------
    # Raman export workflow
    # ------------------------------------------------------------------

    def _current_batch_export_labels(self) -> list[str]:
        return current_batch_export_labels(
            traces=self.traces,
            current_plot_mode=self.current_plot_mode,
            batch_specs=self.batch_specs,
            batch_labels=self.batch_labels,
        )

    def _batch_export_mode(self) -> str:
        return batch_export_mode(
            self.current_plot_mode,
            data_are_reference_subtracted=self.batch_data_are_reference_subtracted,
        )

    def export_single_excel(self):
        """Export the processed single spectrum to Excel."""
        if self.processed_spec is None:
            QtWidgets.QMessageBox.warning(
                self,
                "Nothing to export",
                "Run Processing on a single CSV/SPE file first.",
            )
            return

        default_name = default_single_raman_export_filename(self.current_path)

        out_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export single spectrum to Excel",
            default_name,
            "Excel files (*.xlsx);;All files (*.*)",
        )

        if not out_path:
            return

        out_path = ensure_file_extension(out_path, ".xlsx")

        result = self.export_service.export_single_raman(
            processed_spec=self.processed_spec,
            out_path=out_path,
            source_path=self.current_path,
            raw_spec=self.raw_spec,
            include_chart=True,
            include_metadata=self.export_include_metadata_cb.isChecked(),
            engine="auto",
            xlim=self._xlim(),
            y_lock=self.export_y_lock_cb.isChecked(),
            fontsize=12,
            chart_title_mode=self._export_chart_title_mode(),
            chart_title_text=self._export_chart_title_text(),
            y_axis_label_override=self._export_y_axis_label_override(),
        )

        if not result.ok:
            QtWidgets.QMessageBox.critical(
                self,
                result.error_title,
                result.error_message,
            )
            return

        self.status_label.setText(result.status_message)

        QtWidgets.QMessageBox.information(
            self,
            "Export complete",
            f"Saved:\n{result.output_path}",
        )

    def export_batch_excel_qt(self):
        """Export the last processed batch spectra to Excel."""
        if not self.batch_specs:
            QtWidgets.QMessageBox.warning(
                self,
                "Nothing to export",
                "Run Batch Plot first.",
            )
            return

        default_name = default_batch_raman_export_filename(self.batch_folder)

        out_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export batch spectra to Excel",
            default_name,
            "Excel files (*.xlsx);;All files (*.*)",
        )

        if not out_path:
            return

        out_path = ensure_file_extension(out_path, ".xlsx")

        mode = self._batch_export_mode()

        if reference_subtraction_export_warning_needed(
            self.current_plot_mode,
            data_are_reference_subtracted=self.batch_data_are_reference_subtracted,
        ):
            QtWidgets.QMessageBox.information(
                self,
                "Reference subtraction not applied",
                "Reference subtraction changes the spectral data. "
                "The Excel export will use stacked mode unless you click Run Batch Plot "
                "while reference_subtracted_stacked is selected.",
            )

        overlay_labels = self._current_batch_export_labels()

        per_sheet_titles = per_sheet_titles_from_specs(self.batch_specs)

        stack_offset = None

        if batch_mode_needs_stack_offset(mode):
            visible_traces = [tr for tr in self.traces if tr.get("visible", True)]
            if visible_traces:
                stack_offset = self._stack_offset_value_from_traces(visible_traces)
            else:
                stack_offset = self._stack_offset_value(self.batch_specs)

        title_mode = self._export_chart_title_mode()

        overlay_title = overlay_title_for_batch(
            mode=mode,
            chart_title_mode=title_mode,
            chart_title_text=self._export_chart_title_text(),
        )

        result = self.export_service.export_batch_raman(
            batch_specs=self.batch_specs,
            out_path=out_path,
            processed_files=self.batch_files_processed,
            xlim=self._xlim(),
            batch_plot_mode=mode,
            stack_offset=stack_offset,
            y_lock=self.export_y_lock_cb.isChecked(),
            fontsize=12,
            chart_title_mode=title_mode,
            chart_title_text=self._export_chart_title_text(),
            overlay_legend=self.export_overlay_legend_cb.isChecked(),
            overlay_labels=overlay_labels,
            overlay_title=(overlay_title if overlay_title else None),
            per_sheet_titles=per_sheet_titles,
            y_axis_label_override=self._export_y_axis_label_override(),
        )

        if not result.ok:
            QtWidgets.QMessageBox.critical(
                self,
                result.error_title,
                result.error_message,
            )
            return

        self.status_label.setText(result.status_message)

        QtWidgets.QMessageBox.information(
            self,
            "Export complete",
            f"Saved:\n{result.output_path}",
        )


    # ------------------------------------------------------------------
    # Library workflow
    # ------------------------------------------------------------------

    def add_current_to_library(self):
        result = self.library_service.add_reference(
            processed_spec=self.processed_spec,
            raw_spec=self.raw_spec,
            source_path=self.current_path,
            compound_text=self.library_compound_edit.text(),
            concentration_text=self.library_conc_edit.text(),
            notes_text=self.library_notes_edit.text(),
        )

        if not result.ok:
            if result.error_title == "Library save failed":
                QtWidgets.QMessageBox.critical(
                    self,
                    result.error_title,
                    result.error_message,
                )
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    result.error_title,
                    result.error_message,
                )
            return

        self.status_label.setText(result.status_message)

        QtWidgets.QMessageBox.information(
            self,
            "Reference added",
            result.user_message,
        )

    def search_current_library(self):
        result = self.library_service.search_unknown(
            processed_spec=self.processed_spec,
            raw_spec=self.raw_spec,
            source_path=self.current_path,
            xlim=self._xlim(),
            top_n=10,
        )

        if not result.ok:
            if result.error_title == "Library search failed":
                QtWidgets.QMessageBox.critical(
                    self,
                    result.error_title,
                    result.error_message,
                )
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    result.error_title,
                    result.error_message,
                )
            return

        rows = result.table_rows or []

        self.library_results_table.setRowCount(len(rows))

        for row_idx, values in enumerate(rows):
            for col_idx, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.library_results_table.setItem(row_idx, col_idx, item)

        self.library_results_table.resizeColumnsToContents()
        self.status_label.setText(result.status_message)


    # ------------------------------------------------------------------
    # Trace and plot delegates
    # ------------------------------------------------------------------

    def _make_trace(self, *, spec, label: str, role: str, file: str, visible: bool = True, color_index: int = 0):
        return make_trace(
            spec=spec,
            label=label,
            role=role,
            file=file,
            visible=visible,
            color_index=color_index,
        )

    def _set_traces(self, traces: list[dict]):
        self.traces = traces
        self._refresh_trace_table()
        self.redraw_current_plot()
        if hasattr(self, "analysis_tabs"):
            self.analysis_tabs.setCurrentIndex(0)  # Traces

    def _refresh_trace_table(self):
        self.plot_controller.refresh_trace_table()

    def _trace_table_changed(self, row: int, column: int):
        self.plot_controller.trace_table_changed(row, column)

    def _reset_plot(self):
        self.plot_controller.reset_plot()

    def redraw_current_plot(self):
        self.plot_controller.redraw_current_plot()

    def _trace_xy(self, tr: dict):
        return trace_xy(tr)

    def _pen_for_trace(self, tr, index: int, clean: bool = False):
        return self.plot_controller.pen_for_trace(tr, index, clean=clean)

    def reset_plot_view(self):
        self.plot_controller.reset_plot_view()

    def autoscale_y(self):
        self.plot_controller.autoscale_y()

    def copy_plot_image(self):
        self.plot_controller.copy_plot_image()

    def save_plot_png(self):
        self.plot_controller.save_plot_png()

    def _toggle_focus_plot(self, enabled: bool):
        self.plot_controller.toggle_focus_plot(enabled)

    def _plot_style_changed(self):
        self.plot_controller.plot_style_changed()

    def _robust_ylim_for_traces(self, traces, xlim, lower=1.0, upper=99.5, pad=0.08):
        return robust_ylim_for_traces(
            traces,
            xlim=xlim,
            lower=lower,
            upper=upper,
            pad=pad,
        )

    def _stack_offset_value_from_traces(self, visible_traces: list[dict]) -> float:
        return stack_offset_value_from_traces(
            visible_traces,
            xlim=self._xlim(),
            stack_offset_text=self.stack_offset_edit.text(),
        )

    def _stack_offset_value(self, specs) -> float:
        return stack_offset_value(
            specs,
            xlim=self._xlim(),
            stack_offset_text=self.stack_offset_edit.text(),
        )


    # ------------------------------------------------------------------
    # Peak and ROI drawing/interaction
    # ------------------------------------------------------------------

    def _draw_peak_markers(self, visible_traces: list[dict]):
        """Draw vertical peak markers and labels."""
        if not self.peak_markers:
            return

        mode = self.current_plot_mode
        if mode == "single":
            mode = "overlay"

        y_values = []

        if visible_traces:
            stack_offset = 0.0

            if mode in ("stacked", "reference_subtracted_stacked"):
                stack_offset = self._stack_offset_value_from_traces(visible_traces)

            for i, tr in enumerate(visible_traces):
                x, y = self._trace_xy(tr)
                y = np.asarray(y, dtype=float)

                if mode in ("stacked", "reference_subtracted_stacked"):
                    y = y + i * stack_offset

                finite = np.isfinite(y)

                if np.any(finite):
                    y_values.append(y[finite])

        if y_values:
            yy = np.concatenate(y_values)
            y_text = float(np.nanmax(yy))
        else:
            y_text = 0.0

        for marker in self.peak_markers:
            if not marker.visible:
                continue

            line = pg.InfiniteLine(
                pos=marker.x,
                angle=90,
                movable=True,
                pen=pg.mkPen(
                    "k",
                    width=1.2,
                    style=QtCore.Qt.PenStyle.DashLine,
                ),
                hoverPen=pg.mkPen(
                    "r",
                    width=1.6,
                    style=QtCore.Qt.PenStyle.DashLine,
                ),
            )

            line.sigPositionChangeFinished.connect(
                lambda *args, m=marker, ln=line: self._peak_line_moved(m, ln)
            )

            self._marker_lines.append(line)
            self.plot_widget.addItem(line, ignoreBounds=True)

            label_text = marker.label or f"{marker.x:.1f} cm⁻¹"

            text = pg.TextItem(
                text=label_text,
                anchor=(0, 1),
            )
            text.setPos(marker.x, y_text)
            self.plot_widget.addItem(text)

    def _draw_region_markers(self):
        """Draw movable ROI regions."""
        if not self.region_markers:
            return

        role_colors = {
            "peak": (255, 180, 0, 45),
            "noise": (120, 120, 255, 45),
            "normalization": (0, 180, 120, 45),
            "baseline_exclude": (255, 80, 80, 45),
            "integration": (180, 0, 255, 45),
        }

        for region in self.region_markers:
            if not region.visible:
                continue

            limits = normalize_roi_limits(region.xmin, region.xmax)
            lo = limits.xmin
            hi = limits.xmax

            color = role_colors.get(region.role, (180, 180, 180, 45))

            item = pg.LinearRegionItem(
                values=(lo, hi),
                orientation=pg.LinearRegionItem.Vertical,
                movable=True,
                brush=color,
            )

            item.setZValue(-10)

            item.sigRegionChangeFinished.connect(
                lambda roi_item, r=region: self._roi_region_moved(r, roi_item)
            )

            self._roi_items.append(item)
            self.plot_widget.addItem(item, ignoreBounds=True)

            label_text = region.label or f"{lo:.0f}–{hi:.0f}"

            text = pg.TextItem(
                text=label_text,
                anchor=(0, 0),
            )

            text.setPos(lo, 0)
            self.plot_widget.addItem(text)

    def _roi_region_moved(self, region: RegionMarker, roi_item: pg.LinearRegionItem):
        """Update ROI data when user drags/resizes a region."""
        try:
            lo, hi = roi_item.getRegion()
        except Exception:
            return

        try:
            limits = normalize_roi_limits(lo, hi)
        except ValueError:
            return

        region.xmin = limits.xmin
        region.xmax = limits.xmax

        if should_auto_update_roi_label(region.label, region.role):
            region.label = roi_default_label(region.role, region.xmin, region.xmax)

        self._refresh_roi_table()
        self.status_label.setText(
            f"Moved ROI: {region.xmin:.2f}–{region.xmax:.2f} cm⁻¹."
        )

    def _peak_line_moved(self, marker: PeakMarker, line: pg.InfiniteLine):
        """Update marker data when user drags a marker line."""
        try:
            new_x = float(line.value())
        except Exception:
            return

        marker.x = new_x

        # If the label is still the default cm⁻¹ label, update it automatically.
        old_label = str(marker.label or "")
        if old_label.endswith("cm⁻¹"):
            marker.label = f"{new_x:.1f} cm⁻¹"

        self._refresh_peak_table()
        self.redraw_current_plot()
        self.status_label.setText(f"Moved marker to {new_x:.2f} cm⁻¹.")

    def _refresh_roi_table(self):
        self.analysis_controller.refresh_roi_table()

    def _roi_role_changed(self, row: int, role: str):
        self.analysis_controller.roi_role_changed(row, role)

    def _roi_table_changed(self, row: int, column: int):
        self.analysis_controller.roi_table_changed(row, column)

    def add_roi_from_view(self):
        self.analysis_controller.add_roi_from_view()

    def add_roi_manual(self):
        self.analysis_controller.add_roi_manual()

    def _add_region_marker(self, xmin: float, xmax: float, role: str = "peak"):
        """Add a region marker and redraw."""
        try:
            limits = normalize_roi_limits(xmin, xmax)
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(
                self,
                "Invalid ROI",
                str(exc),
            )
            return

        role = str(role or "peak").strip().lower()
        lo = limits.xmin
        hi = limits.xmax
        label = roi_default_label(role, lo, hi)

        region = RegionMarker(
            xmin=lo,
            xmax=hi,
            label=label,
            role=role,
            visible=True,
        )

        self.region_markers.append(region)
        self._refresh_roi_table()
        self.redraw_current_plot()

        if hasattr(self, "analysis_tabs"):
            self.analysis_tabs.setCurrentIndex(3)  # ROIs

        self.status_label.setText(f"Added ROI: {lo:.2f}–{hi:.2f} cm⁻¹.")

    def clear_region_markers(self):
        self.analysis_controller.clear_region_markers()

    def _refresh_peak_table(self):
        self.analysis_controller.refresh_peak_table()

    def _peak_table_changed(self, row: int, column: int):
        self.analysis_controller.peak_table_changed(row, column)

    def _nearest_y_for_trace(self, tr: dict, x0: float) -> float:
        return nearest_y_for_trace(tr, x0)

    def _peak_value_for_trace(self, tr: dict, x0: float) -> float:
        method = "nearest"

        if hasattr(self, "peak_intensity_method_combo"):
            method = self.peak_intensity_method_combo.currentText().lower()

        return peak_value_for_trace(
            tr,
            x0,
            method=method,
            half_window_cm1=self._peak_window_cm1(),
        )

    def _peak_intensity_matrix(self):
        method = "nearest"

        if hasattr(self, "peak_intensity_method_combo"):
            method = self.peak_intensity_method_combo.currentText().lower()

        return peak_intensity_matrix(
            traces=self.traces,
            markers=self.peak_markers,
            method=method,
            half_window_cm1=self._peak_window_cm1(),
        )

    def _refresh_peak_intensity_table(self):
        self.analysis_controller.refresh_peak_intensity_table()

    def _peak_intensity_summary(self, x0: float, traces: list[dict]) -> str:
        return peak_intensity_summary(x0, traces)

    def _peak_window_cm1(self) -> float:
        text = self.peak_window_edit.text() if hasattr(self, "peak_window_edit") else "5"
        return safe_peak_window_cm1(text)

    def copy_peak_intensity_table(self):
        self.analysis_controller.copy_peak_intensity_table()

    def export_peak_intensity_csv(self):
        self.analysis_controller.export_peak_intensity_csv()

    def _set_peak_pick_mode(self, enabled: bool):
        """Enable/disable click-to-place peak marker mode."""
        self.peak_pick_mode = bool(enabled)

        # Keep toolbar and Plot-tab buttons synchronized.
        for btn_name in ("pick_peak_btn", "add_marker_btn"):
            if hasattr(self, btn_name):
                btn = getattr(self, btn_name)
                if btn.isChecked() != self.peak_pick_mode:
                    btn.blockSignals(True)
                    btn.setChecked(self.peak_pick_mode)
                    btn.blockSignals(False)

        if self.peak_pick_mode:
            self.plot_widget.setCursor(QtCore.Qt.CursorShape.CrossCursor)
            self.status_label.setText("Peak picking mode: click on the plot to place a marker.")
        else:
            self.plot_widget.unsetCursor()
            self.status_label.setText("Peak picking mode off.")

    def add_peak_marker_at_cursor(self):
        self.analysis_controller.add_peak_marker_at_cursor()

    def add_peak_marker_manual(self):
        self.analysis_controller.add_peak_marker_manual()

    def _add_peak_marker(self, x: float):
        """Add marker object and redraw."""
        marker = PeakMarker(
            x=float(x),
            label=f"{float(x):.1f} cm⁻¹",
            visible=True,
        )

        self.peak_markers.append(marker)
        self._refresh_peak_table()
        self.redraw_current_plot()
        if hasattr(self, "analysis_tabs"):
            self.analysis_tabs.setCurrentIndex(1)  # Peak markers
        self.status_label.setText(f"Added marker at {x:.2f} cm⁻¹.")

    def clear_peak_markers(self):
        self.analysis_controller.clear_peak_markers()


    # ------------------------------------------------------------------
    # Cursor, mouse, and keyboard events
    # ------------------------------------------------------------------

    def _plot_mouse_clicked(self, event):
        """Place a peak marker only when peak-picking mode is active."""
        if not self.peak_pick_mode:
            return

        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return

        pos = event.scenePos()

        if not self.plot_widget.sceneBoundingRect().contains(pos):
            return

        mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
        x = float(mouse_point.x())

        self._add_peak_marker(x)
        self._set_peak_pick_mode(False)

        try:
            event.accept()
        except Exception:
            pass

    def _mouse_moved(self, event):
        pos = event[0]
        if self.plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
            x = mouse_point.x()
            y = mouse_point.y()
            
            self.last_cursor_x = float(x)
            self.last_cursor_y = float(y)
            
            self.vline.setPos(x)
            self.hline.setPos(y)
            if self.current_plot_mode == "paax":
                self.cursor_label.setText(f"Cursor: {x:.4g}, {y:.4g}")
            else:
                self.cursor_label.setText(f"Cursor: {x:.2f} cm⁻¹, {y:.2f}")
            self._update_nearest_label(x)

    def _update_nearest_label(self, x_cursor: float):
        visible_traces = [tr for tr in self.traces if tr.get("visible", True)]

        if not visible_traces:
            self.nearest_label.setText("Nearest: —")
            return

        tr = visible_traces[0]
        x, y = self._trace_xy(tr)

        if x.size == 0 or y.size == 0:
            self.nearest_label.setText("Nearest: —")
            return

        finite = np.isfinite(x) & np.isfinite(y)

        if not np.any(finite):
            self.nearest_label.setText("Nearest: —")
            return

        x_f = x[finite]
        y_f = y[finite]

        idx = int(np.nanargmin(np.abs(x_f - x_cursor)))

        label = str(tr.get("label", "trace"))

        if str(tr.get("kind", "")).lower() == "paax":
            self.nearest_label.setText(
                f"Nearest [{label}]: {x_f[idx]:.4g}, {y_f[idx]:.4g}"
            )
        else:
            self.nearest_label.setText(
                f"Nearest [{label}]: {x_f[idx]:.2f} cm⁻¹, {y_f[idx]:.2f}"
            )

    def keyPressEvent(self, event):
        """Esc cancels peak-picking mode."""
        if event.key() == QtCore.Qt.Key.Key_Escape and self.peak_pick_mode:
            self._set_peak_pick_mode(False)
            event.accept()
            return

        super().keyPressEvent(event)

def main():
    app = QtWidgets.QApplication(sys.argv)
    pg.setConfigOptions(antialias=True)
    win = SpectralViewer()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
