from __future__ import annotations

from PySide6 import QtCore, QtWidgets


def build_export_tab(window):
    tab = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(tab)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(10)

    title = QtWidgets.QLabel("Excel Export")
    title.setStyleSheet("font-size: 15px; font-weight: 600;")
    layout.addWidget(title)

    subtitle = QtWidgets.QLabel(
        "Export the currently processed single spectrum or the last processed batch "
        "using publication-style Excel chart formatting."
    )
    subtitle.setWordWrap(True)
    subtitle.setStyleSheet("color: #666;")
    layout.addWidget(subtitle)

    action_box = QtWidgets.QGroupBox("Workbook export")
    action_layout = QtWidgets.QVBoxLayout(action_box)

    window.export_single_btn = QtWidgets.QPushButton("Export single processed spectrum…")
    window.export_single_btn.clicked.connect(window.export_single_excel)
    window.export_single_btn.setMinimumHeight(34)
    action_layout.addWidget(window.export_single_btn)

    single_hint = QtWidgets.QLabel(
        "Uses the spectrum created by Run Processing in the Single tab."
    )
    single_hint.setWordWrap(True)
    single_hint.setStyleSheet("color: #777;")
    action_layout.addWidget(single_hint)

    window.export_batch_btn = QtWidgets.QPushButton("Export last processed batch…")
    window.export_batch_btn.clicked.connect(window.export_batch_excel_qt)
    window.export_batch_btn.setMinimumHeight(34)
    action_layout.addWidget(window.export_batch_btn)

    batch_hint = QtWidgets.QLabel(
        "Uses the spectra created by Run Batch Processing + Plot in the Batch tab."
    )
    batch_hint.setWordWrap(True)
    batch_hint.setStyleSheet("color: #777;")
    action_layout.addWidget(batch_hint)

    layout.addWidget(action_box)

    chart_box = QtWidgets.QGroupBox("Excel chart style")
    chart_form = QtWidgets.QFormLayout(chart_box)
    chart_form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

    style_note = QtWidgets.QLabel(
        "Fixed chart format: x-axis 400–1700 cm⁻¹ from Plot tab range, "
        "0-decimal x labels, outside tick marks, no gridlines."
    )
    style_note.setWordWrap(True)
    style_note.setStyleSheet("color: #777;")
    chart_form.addRow("", style_note)

    window.export_y_label_edit = QtWidgets.QLineEdit("")
    window.export_y_label_edit.setPlaceholderText(
        "blank = automatic, e.g. Intensity (ADU mW⁻¹ s⁻¹)"
    )
    chart_form.addRow("Y-axis label", window.export_y_label_edit)

    window.export_title_mode_combo = QtWidgets.QComboBox()
    window.export_title_mode_combo.addItems(["blank", "sample", "custom"])
    window.export_title_mode_combo.setCurrentText("blank")
    chart_form.addRow("Chart title", window.export_title_mode_combo)

    window.export_title_text_edit = QtWidgets.QLineEdit("")
    window.export_title_text_edit.setPlaceholderText("used only when title mode is custom")
    chart_form.addRow("Custom title", window.export_title_text_edit)

    layout.addWidget(chart_box)

    option_box = QtWidgets.QGroupBox("Workbook options")
    option_layout = QtWidgets.QVBoxLayout(option_box)

    window.export_include_metadata_cb = QtWidgets.QCheckBox("Include metadata sheet")
    window.export_include_metadata_cb.setChecked(True)
    option_layout.addWidget(window.export_include_metadata_cb)

    window.export_y_lock_cb = QtWidgets.QCheckBox("Lock y-axis from 0 to 1.05× maximum")
    window.export_y_lock_cb.setChecked(True)
    option_layout.addWidget(window.export_y_lock_cb)

    window.export_overlay_legend_cb = QtWidgets.QCheckBox("Show legend on batch overlay chart")
    window.export_overlay_legend_cb.setChecked(True)
    option_layout.addWidget(window.export_overlay_legend_cb)

    layout.addWidget(option_box)

    footer = QtWidgets.QLabel(
        "Tip: adjust the x-axis range in the Plot tab before exporting. "
        "Default thesis range is 400–1700 cm⁻¹."
    )
    footer.setWordWrap(True)
    footer.setStyleSheet("color: #777;")
    layout.addWidget(footer)

    layout.addStretch()
    window.tabs.addTab(tab, "Export")