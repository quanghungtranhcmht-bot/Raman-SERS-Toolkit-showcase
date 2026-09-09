from __future__ import annotations

from PySide6 import QtWidgets


def build_single_tab(window):
    tab = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(tab)

    window.open_btn = QtWidgets.QPushButton("Open CSV/SPE")
    window.open_btn.clicked.connect(window.open_spectrum)
    layout.addWidget(window.open_btn)

    window.file_label = QtWidgets.QLabel("No file loaded")
    window.file_label.setWordWrap(True)
    layout.addWidget(window.file_label)

    window.process_btn = QtWidgets.QPushButton("Run Processing")
    window.process_btn.clicked.connect(window.run_processing)
    layout.addWidget(window.process_btn)

    window.show_raw_cb = QtWidgets.QCheckBox("Show raw")
    window.show_raw_cb.setChecked(True)
    window.show_raw_cb.stateChanged.connect(window.update_single_traces)
    layout.addWidget(window.show_raw_cb)

    window.show_processed_cb = QtWidgets.QCheckBox("Show processed")
    window.show_processed_cb.setChecked(True)
    window.show_processed_cb.stateChanged.connect(window.update_single_traces)
    layout.addWidget(window.show_processed_cb)

    window.show_baseline_cb = QtWidgets.QCheckBox("Show estimated baseline")
    window.show_baseline_cb.setChecked(False)
    window.show_baseline_cb.stateChanged.connect(window.update_single_traces)
    layout.addWidget(window.show_baseline_cb)

    layout.addStretch()
    window.tabs.addTab(tab, "Single")