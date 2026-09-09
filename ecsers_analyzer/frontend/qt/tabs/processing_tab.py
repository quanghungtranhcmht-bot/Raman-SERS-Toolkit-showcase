from __future__ import annotations

from PySide6 import QtWidgets


def build_processing_tab(window):
    tab = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(tab)
    form = QtWidgets.QFormLayout()

    window.baseline_combo = QtWidgets.QComboBox()
    window.baseline_combo.addItems(["none", "airpls", "als", "poly"])
    window.baseline_combo.setCurrentText("airpls")
    form.addRow("Baseline", window.baseline_combo)

    window.lam_edit = QtWidgets.QLineEdit("1e5")
    form.addRow("airPLS λ", window.lam_edit)

    window.iter_edit = QtWidgets.QLineEdit("80")
    form.addRow("airPLS max iterations", window.iter_edit)

    window.despike_cb = QtWidgets.QCheckBox("Remove cosmic-ray spikes")
    window.despike_cb.setChecked(False)
    form.addRow("", window.despike_cb)

    window.despike_window_edit = QtWidgets.QLineEdit("7")
    form.addRow("Despike window", window.despike_window_edit)

    window.despike_threshold_edit = QtWidgets.QLineEdit("7.0")
    form.addRow("Despike threshold", window.despike_threshold_edit)

    window.despike_max_width_edit = QtWidgets.QLineEdit("1")
    form.addRow("Maximum spike width (points)", window.despike_max_width_edit)

    def update_despike_controls(*_):
        enabled = window.despike_cb.isChecked()
        window.despike_window_edit.setEnabled(enabled)
        window.despike_threshold_edit.setEnabled(enabled)
        window.despike_max_width_edit.setEnabled(enabled)

    window.despike_cb.stateChanged.connect(update_despike_controls)
    update_despike_controls()

    window.smooth_cb = QtWidgets.QCheckBox("Apply Savitzky-Golay smoothing")
    window.smooth_cb.setChecked(False)
    form.addRow("", window.smooth_cb)

    window.smooth_edit = QtWidgets.QLineEdit("5")
    form.addRow("SavGol window, points", window.smooth_edit)

    window.smooth_cm1_cb = QtWidgets.QCheckBox("Define smoothing width in cm⁻¹")
    window.smooth_cm1_cb.setChecked(True)
    form.addRow("", window.smooth_cm1_cb)

    window.smooth_cm1_edit = QtWidgets.QLineEdit("8")
    form.addRow("SavGol width, cm⁻¹", window.smooth_cm1_edit)

    window.smooth_poly_edit = QtWidgets.QLineEdit("2")
    form.addRow("SavGol polyorder", window.smooth_poly_edit)

    window.norm_combo = QtWidgets.QComboBox()
    window.norm_combo.addItems(["none", "max", "area", "vector", "power_time"])
    window.norm_combo.setCurrentText("none")
    form.addRow("Normalization", window.norm_combo)

    window.power_edit = QtWidgets.QLineEdit("34.1")
    form.addRow("Laser power (mW)", window.power_edit)

    def update_smoothing_controls(*_):
        smoothing_on = window.smooth_cb.isChecked()
        width_mode = smoothing_on and window.smooth_cm1_cb.isChecked()
        window.smooth_cm1_cb.setEnabled(smoothing_on)
        window.smooth_edit.setEnabled(smoothing_on and not width_mode)
        window.smooth_cm1_edit.setEnabled(width_mode)
        window.smooth_poly_edit.setEnabled(smoothing_on)

    window.smooth_cb.stateChanged.connect(update_smoothing_controls)
    window.smooth_cm1_cb.stateChanged.connect(update_smoothing_controls)
    update_smoothing_controls()

    window.recommend_processing_btn = QtWidgets.QPushButton("Recommend Processing Settings")
    window.recommend_processing_btn.clicked.connect(window.recommend_processing_settings)
    layout.addWidget(window.recommend_processing_btn)

    layout.addLayout(form)

    info = QtWidgets.QLabel(
        "Processing settings are applied explicitly and stored for later use. "
        "After changing any settings, run processing again to update the spectrum."
    )
    info.setWordWrap(True)
    layout.addWidget(info)

    for widget in [
        window.baseline_combo,
        window.lam_edit,
        window.iter_edit,
        window.despike_cb,
        window.despike_window_edit,
        window.despike_threshold_edit,
        window.despike_max_width_edit,
        window.smooth_cb,
        window.smooth_edit,
        window.smooth_cm1_cb,
        window.smooth_cm1_edit,
        window.smooth_poly_edit,
        window.norm_combo,
        window.power_edit,
    ]:
        if isinstance(widget, QtWidgets.QComboBox):
            widget.currentTextChanged.connect(window._processing_settings_changed)
        elif isinstance(widget, QtWidgets.QCheckBox):
            widget.stateChanged.connect(window._processing_settings_changed)
        elif isinstance(widget, QtWidgets.QLineEdit):
            widget.editingFinished.connect(window._processing_settings_changed)

    layout.addStretch()
    window.tabs.addTab(tab, "Processing")