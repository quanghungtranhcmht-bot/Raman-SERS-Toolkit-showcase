from __future__ import annotations

from PySide6 import QtWidgets


def build_library_tab(window):
    tab = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(tab)

    title = QtWidgets.QLabel("SERS Spectral Library")
    title.setStyleSheet("font-size: 15px; font-weight: 600;")
    layout.addWidget(title)

    note = QtWidgets.QLabel(
        "Save processed reference spectra and search unknown spectra against the library."
    )
    note.setWordWrap(True)
    note.setStyleSheet("color: #666;")
    layout.addWidget(note)

    form = QtWidgets.QFormLayout()

    window.library_compound_edit = QtWidgets.QLineEdit("")
    window.library_compound_edit.setPlaceholderText("e.g. Quercetin")
    form.addRow("Compound", window.library_compound_edit)

    window.library_conc_edit = QtWidgets.QLineEdit("")
    window.library_conc_edit.setPlaceholderText("optional, e.g. 5e-5")
    form.addRow("Concentration M", window.library_conc_edit)

    window.library_notes_edit = QtWidgets.QLineEdit("")
    window.library_notes_edit.setPlaceholderText("optional notes")
    form.addRow("Notes", window.library_notes_edit)

    layout.addLayout(form)

    window.add_reference_btn = QtWidgets.QPushButton("Add current processed spectrum to library")
    window.add_reference_btn.clicked.connect(window.add_current_to_library)
    layout.addWidget(window.add_reference_btn)

    window.search_library_btn = QtWidgets.QPushButton("Search current processed spectrum")
    window.search_library_btn.clicked.connect(window.search_current_library)
    layout.addWidget(window.search_library_btn)

    window.library_results_table = QtWidgets.QTableWidget(0, 4)
    window.library_results_table.setHorizontalHeaderLabels([
        "Rank",
        "Compound",
        "Score",
        "Reference ID",
    ])
    window.library_results_table.horizontalHeader().setStretchLastSection(True)
    window.library_results_table.verticalHeader().setVisible(False)
    layout.addWidget(window.library_results_table)

    layout.addStretch()
    window.tabs.addTab(tab, "Library")