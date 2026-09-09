from __future__ import annotations

from pathlib import Path
import sys
import unittest

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ecsers_analyzer.domain.spectrum import Spectrum
from ecsers_analyzer.plotting.trace_builder import (
    axis_y_label_for_spec,
    build_batch_traces,
    build_single_traces,
    stack_offset_value_from_traces,
    trace_xy,
)


class PlotTraceBuilderTests(unittest.TestCase):
    def test_single_traces_include_raw_processed_and_baseline(self):
        x = np.array([400.0, 500.0, 600.0])
        raw = Spectrum(x, np.array([1.0, 2.0, 3.0]))
        processed = Spectrum(x, np.array([0.1, 0.2, 0.3]))
        processed.baseline = np.array([0.9, 0.8, 0.7])

        traces = build_single_traces(
            raw_spec=raw,
            processed_spec=processed,
            file_name="sample.csv",
            show_raw=True,
            show_processed=True,
            show_baseline=True,
        )

        roles = [tr["role"] for tr in traces]

        self.assertEqual(roles, ["raw", "processed", "baseline"])
        self.assertEqual(traces[0]["label"], "Raw")
        self.assertEqual(traces[1]["label"], "Processed")
        self.assertEqual(traces[2]["label"], "Estimated baseline")
        self.assertEqual(traces[0]["file"], "sample.csv")

    def test_single_traces_skip_baseline_when_unavailable(self):
        x = np.array([400.0, 500.0, 600.0])
        raw = Spectrum(x, np.array([1.0, 2.0, 3.0]))
        processed = Spectrum(x, np.array([0.1, 0.2, 0.3]))

        traces = build_single_traces(
            raw_spec=raw,
            processed_spec=processed,
            file_name="sample.csv",
            show_raw=True,
            show_processed=True,
            show_baseline=True,
        )

        roles = [tr["role"] for tr in traces]

        self.assertEqual(roles, ["raw", "processed"])

    def test_batch_traces_use_reference_subtracted_role(self):
        x = np.array([400.0, 500.0, 600.0])
        specs = [
            Spectrum(x, np.array([1.0, 2.0, 3.0])),
            Spectrum(x, np.array([2.0, 3.0, 4.0])),
        ]

        traces = build_batch_traces(
            specs=specs,
            labels=["OCP", "-0.3 V"],
            files=["ocp.spe", "minus03.spe"],
            mode="reference_subtracted_stacked",
        )

        self.assertEqual(len(traces), 2)
        self.assertEqual(traces[0]["role"], "ref-sub processed")
        self.assertEqual(traces[1]["role"], "ref-sub processed")
        self.assertEqual(traces[0]["label"], "OCP")
        self.assertEqual(traces[1]["file"], "minus03.spe")

    def test_trace_xy_uses_raw_processed_and_baseline_arrays(self):
        x = np.array([400.0, 500.0, 600.0])
        spec = Spectrum(x, np.array([10.0, 20.0, 30.0]))

        spec.x = x.copy()
        spec.y = np.array([1.0, 2.0, 3.0])
        spec.baseline = np.array([9.0, 18.0, 27.0])

        raw_x, raw_y = trace_xy({"spec": spec, "role": "raw"})
        proc_x, proc_y = trace_xy({"spec": spec, "role": "processed"})
        base_x, base_y = trace_xy({"spec": spec, "role": "baseline"})

        np.testing.assert_allclose(raw_x, spec.x_raw)
        np.testing.assert_allclose(raw_y, spec.y_raw)

        np.testing.assert_allclose(proc_x, spec.x)
        np.testing.assert_allclose(proc_y, spec.y)

        np.testing.assert_allclose(base_x, spec.x_raw)
        np.testing.assert_allclose(base_y, spec.baseline)

    def test_auto_stack_offset_uses_visible_x_range(self):
        x = np.array([400.0, 500.0, 1800.0])
        spec = Spectrum(x, np.array([0.0, 10.0, 1000.0]))

        traces = [
            {
                "spec": spec,
                "role": "processed",
                "label": "trace",
                "visible": True,
                "color_index": 0,
            }
        ]

        offset = stack_offset_value_from_traces(
            traces,
            xlim=(400.0, 600.0),
            stack_offset_text="auto",
        )

        self.assertAlmostEqual(offset, 12.0)

    def test_manual_stack_offset_overrides_auto(self):
        x = np.array([400.0, 500.0, 600.0])
        spec = Spectrum(x, np.array([0.0, 10.0, 20.0]))

        traces = [
            {
                "spec": spec,
                "role": "processed",
                "label": "trace",
                "visible": True,
                "color_index": 0,
            }
        ]

        offset = stack_offset_value_from_traces(
            traces,
            xlim=(400.0, 600.0),
            stack_offset_text="50",
        )

        self.assertEqual(offset, 50.0)

    def test_axis_y_label_follows_normalization(self):
        x = np.array([400.0, 500.0, 600.0])
        spec = Spectrum(x, np.array([1.0, 2.0, 3.0]))

        self.assertEqual(axis_y_label_for_spec(spec), "Intensity (a.u.)")

        spec.normalization_method = "power_time"
        self.assertEqual(axis_y_label_for_spec(spec), "Intensity (ADU mW⁻¹ s⁻¹)")

        spec.normalization_method = "max"
        self.assertEqual(axis_y_label_for_spec(spec), "Normalized Intensity (a.u.)")


if __name__ == "__main__":
    unittest.main()