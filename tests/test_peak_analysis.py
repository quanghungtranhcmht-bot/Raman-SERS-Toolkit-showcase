from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ecsers_analyzer.plotting.peak_analysis import (
    nearest_y_for_trace,
    peak_intensity_matrix,
    peak_intensity_summary,
    peak_value_for_trace,
    robust_ylim_for_traces,
    safe_peak_window_cm1,
)


def make_trace(label="sample", y=None, visible=True):
    if y is None:
        y = [1.0, 5.0, 2.0, 8.0]

    spec = SimpleNamespace(
        x=np.asarray([400.0, 500.0, 600.0, 700.0], dtype=float),
        y=np.asarray(y, dtype=float),
    )

    return {
        "spec": spec,
        "label": label,
        "role": "processed",
        "file": f"{label}.csv",
        "visible": visible,
    }


def make_marker(x=500.0, label="", visible=True):
    return SimpleNamespace(
        x=x,
        label=label,
        visible=visible,
    )


class PeakAnalysisTests(unittest.TestCase):
    def test_safe_peak_window_cm1(self):
        self.assertEqual(safe_peak_window_cm1("7"), 7.0)
        self.assertEqual(safe_peak_window_cm1("-7"), 7.0)
        self.assertEqual(safe_peak_window_cm1("0"), 5.0)
        self.assertEqual(safe_peak_window_cm1("bad"), 5.0)

    def test_nearest_y_for_trace(self):
        trace = make_trace()

        self.assertEqual(nearest_y_for_trace(trace, 510.0), 5.0)

    def test_nearest_y_for_non_finite_trace(self):
        trace = make_trace(y=[np.nan, np.nan, np.nan, np.nan])

        self.assertTrue(np.isnan(nearest_y_for_trace(trace, 500.0)))

    def test_peak_value_for_trace_nearest(self):
        trace = make_trace()

        value = peak_value_for_trace(
            trace,
            510.0,
            method="nearest",
        )

        self.assertEqual(value, 5.0)

    def test_peak_value_for_trace_local_max_window(self):
        trace = make_trace()

        value = peak_value_for_trace(
            trace,
            650.0,
            method="local_max_window",
            half_window_cm1=60.0,
        )

        self.assertEqual(value, 8.0)

    def test_peak_intensity_matrix(self):
        traces = [make_trace(label="sample")]
        markers = [make_marker(x=500.0, label="500 cm⁻¹")]

        headers, rows = peak_intensity_matrix(
            traces=traces,
            markers=markers,
            method="nearest",
            half_window_cm1=5.0,
        )

        self.assertEqual(headers, ["Trace", "Role", "File", "500 cm⁻¹"])
        self.assertEqual(rows[0][:3], ["sample", "processed", "sample.csv"])
        self.assertEqual(rows[0][3], 5.0)

    def test_peak_intensity_summary(self):
        traces = [make_trace(label="sample")]

        text = peak_intensity_summary(500.0, traces)

        self.assertEqual(text, "sample: 5")

    def test_robust_ylim_for_traces(self):
        traces = [make_trace(y=[1.0, 2.0, 3.0, 100.0])]

        ylim = robust_ylim_for_traces(
            traces,
            xlim=(400, 700),
            lower=0,
            upper=100,
            pad=0,
        )

        self.assertEqual(ylim, (1.0, 100.0))


if __name__ == "__main__":
    unittest.main()