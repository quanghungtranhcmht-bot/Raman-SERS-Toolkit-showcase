from __future__ import annotations

from PySide6 import QtWidgets


def build_ec_tab(window):
    tab = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(tab)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(10)

    title = QtWidgets.QLabel("Electrochemistry / PAAX")
    title.setStyleSheet("font-size: 15px; font-weight: 600;")
    layout.addWidget(title)

    subtitle = QtWidgets.QLabel(
        "Open AfterMath PAAX files and inspect electrochemical traces "
        "such as current, applied potential, or charge versus time."
    )
    subtitle.setWordWrap(True)
    subtitle.setStyleSheet("color: #666;")
    layout.addWidget(subtitle)

    window.open_paax_btn = QtWidgets.QPushButton("Open PAAX…")
    window.open_paax_btn.clicked.connect(window.open_paax)
    window.open_paax_btn.setMinimumHeight(34)
    layout.addWidget(window.open_paax_btn)

    window.paax_file_label = QtWidgets.QLabel("No PAAX file loaded")
    window.paax_file_label.setWordWrap(True)
    window.paax_file_label.setStyleSheet("color: #666;")
    layout.addWidget(window.paax_file_label)

    form = QtWidgets.QFormLayout()

    window.paax_study_combo = QtWidgets.QComboBox()
    window.paax_study_combo.currentTextChanged.connect(window.refresh_paax_trace_dropdown)
    form.addRow("Study", window.paax_study_combo)

    window.paax_trace_combo = QtWidgets.QComboBox()
    form.addRow("Trace", window.paax_trace_combo)

    layout.addLayout(form)

    window.plot_paax_btn = QtWidgets.QPushButton("Plot selected EC trace")
    window.plot_paax_btn.clicked.connect(window.plot_paax_trace)
    window.plot_paax_btn.setMinimumHeight(34)
    layout.addWidget(window.plot_paax_btn)

    window.export_paax_csv_btn = QtWidgets.QPushButton("Export selected trace CSV…")
    window.export_paax_csv_btn.clicked.connect(window.export_paax_selected_csv)
    layout.addWidget(window.export_paax_csv_btn)

    window.export_paax_excel_btn = QtWidgets.QPushButton("Export selected trace Excel…")
    window.export_paax_excel_btn.clicked.connect(window.export_paax_selected_excel)
    layout.addWidget(window.export_paax_excel_btn)

    hint = QtWidgets.QLabel(
        "PAAX traces are plotted as electrochemical time traces. "
        "They are not sent through Raman preprocessing."
    )
    hint.setWordWrap(True)
    hint.setStyleSheet("color: #777;")
    layout.addWidget(hint)

    layout.addStretch()
    window.tabs.addTab(tab, "EC/PAAX")