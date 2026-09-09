from __future__ import annotations

from PySide6 import QtWidgets


def build_plot_tab(window):
    tab = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(tab)
    form = QtWidgets.QFormLayout()

    window.xmin_edit = QtWidgets.QLineEdit("400")
    window.xmax_edit = QtWidgets.QLineEdit("1700")
    window.xmin_edit.editingFinished.connect(window.redraw_current_plot)
    window.xmax_edit.editingFinished.connect(window.redraw_current_plot)

    xrow = QtWidgets.QHBoxLayout()
    xrow.addWidget(window.xmin_edit)
    xrow.addWidget(window.xmax_edit)
    form.addRow("X range", xrow)

    window.show_grid_cb = QtWidgets.QCheckBox("Show grid")
    window.show_grid_cb.setChecked(False)
    window.show_grid_cb.stateChanged.connect(window._plot_style_changed)
    form.addRow("", window.show_grid_cb)

    window.show_legend_cb = QtWidgets.QCheckBox("Show legend")
    window.show_legend_cb.setChecked(True)
    window.show_legend_cb.stateChanged.connect(window.redraw_current_plot)
    form.addRow("", window.show_legend_cb)

    window.clean_figure_cb = QtWidgets.QCheckBox("Clean figure mode")
    window.clean_figure_cb.setChecked(False)
    window.clean_figure_cb.stateChanged.connect(window.redraw_current_plot)
    form.addRow("", window.clean_figure_cb)

    window.show_analysis_panel_cb = QtWidgets.QCheckBox("Show analysis panel")
    window.show_analysis_panel_cb.setChecked(True)
    window.show_analysis_panel_cb.stateChanged.connect(window._toggle_analysis_panel)
    form.addRow("", window.show_analysis_panel_cb)

    layout.addLayout(form)

    window.add_marker_btn = QtWidgets.QPushButton("Pick peak on plot")
    window.add_marker_btn.setCheckable(True)
    window.add_marker_btn.toggled.connect(window._set_peak_pick_mode)
    layout.addWidget(window.add_marker_btn)

    window.add_marker_manual_btn = QtWidgets.QPushButton("Add peak by cm⁻¹")
    window.add_marker_manual_btn.clicked.connect(window.add_peak_marker_manual)
    layout.addWidget(window.add_marker_manual_btn)

    window.clear_markers_btn = QtWidgets.QPushButton("Clear peak markers")
    window.clear_markers_btn.clicked.connect(window.clear_peak_markers)
    layout.addWidget(window.clear_markers_btn)

    hint = QtWidgets.QLabel(
        "Visual settings redraw immediately. Trace visibility and labels can be edited in the trace table."
    )
    hint.setWordWrap(True)
    layout.addWidget(hint)

    layout.addStretch()
    window.tabs.addTab(tab, "Plot")