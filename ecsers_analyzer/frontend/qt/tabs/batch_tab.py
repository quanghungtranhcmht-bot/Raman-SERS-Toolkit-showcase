from __future__ import annotations

from PySide6 import QtWidgets


def build_batch_tab(window):
    tab = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(tab)

    window.open_folder_btn = QtWidgets.QPushButton("Select Batch Folder")
    window.open_folder_btn.clicked.connect(window.open_batch_folder)
    layout.addWidget(window.open_folder_btn)

    window.batch_folder_label = QtWidgets.QLabel("No batch folder selected")
    window.batch_folder_label.setWordWrap(True)
    layout.addWidget(window.batch_folder_label)

    window.batch_list = QtWidgets.QListWidget()
    window.batch_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
    window.batch_list.setMinimumHeight(220)
    layout.addWidget(window.batch_list)

    form = QtWidgets.QFormLayout()

    window.batch_mode_combo = QtWidgets.QComboBox()
    window.batch_mode_combo.addItems(["overlay", "stacked", "reference_subtracted_stacked"])
    window.batch_mode_combo.currentTextChanged.connect(window._batch_mode_changed)
    form.addRow("Plot mode", window.batch_mode_combo)

    window.stack_offset_edit = QtWidgets.QLineEdit("auto")
    window.stack_offset_edit.editingFinished.connect(window.redraw_current_plot)
    form.addRow("Stack offset", window.stack_offset_edit)

    window.reference_combo = QtWidgets.QComboBox()
    form.addRow("Reference", window.reference_combo)

    window.bottom_combo = QtWidgets.QComboBox()
    window.bottom_combo.currentTextChanged.connect(window._bottom_changed)
    form.addRow("Bottom spectrum", window.bottom_combo)

    window.skip_reference_cb = QtWidgets.QCheckBox("Skip reference in corrected plot")
    window.skip_reference_cb.setChecked(True)
    form.addRow("", window.skip_reference_cb)

    layout.addLayout(form)

    window.run_batch_btn = QtWidgets.QPushButton("Run Batch Processing + Plot")
    window.run_batch_btn.clicked.connect(window.run_batch_plot)
    layout.addWidget(window.run_batch_btn)

    layout.addStretch()
    window.tabs.addTab(tab, "Batch")