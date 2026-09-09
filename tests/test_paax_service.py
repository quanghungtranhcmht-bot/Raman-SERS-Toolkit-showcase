from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ecsers_analyzer.services.paax_service import PaaxService


def make_trace(
    *,
    study="Study A",
    name="Current",
    x=None,
    y=None,
):
    if x is None:
        x = np.asarray([0.0, 1.0, 2.0], dtype=float)
    if y is None:
        y = np.asarray([0.1, 0.2, 0.3], dtype=float)

    return SimpleNamespace(
        name=name,
        xlabel="Time (s)",
        ylabel="Current (A)",
        x=np.asarray(x, dtype=float),
        y=np.asarray(y, dtype=float),
        metadata={
            "study_name": study,
        },
    )


class PaaxServiceTests(unittest.TestCase):
    def test_loaded_file_plan_lists_studies(self):
        service = PaaxService()
        traces = [
            make_trace(study="Study B"),
            make_trace(study="Study A"),
            make_trace(study="Study A"),
        ]

        plan = service.loaded_file_plan(
            path="example.paax",
            traces=traces,
        )

        self.assertEqual(plan.studies, ["Study A", "Study B"])
        self.assertIn("example.paax", plan.file_label)
        self.assertIn("Loaded PAAX file", plan.status_message)

    def test_dropdown_plan_filters_traces_by_study(self):
        service = PaaxService()
        traces = [
            make_trace(study="Study A", name="Current"),
            make_trace(study="Study B", name="Voltage"),
        ]

        plan = service.dropdown_plan(
            traces=traces,
            selected_study="Study A",
        )

        self.assertEqual(len(plan.visible_traces), 1)
        self.assertIn("Current", plan.dropdown_labels[0])

    def test_selected_trace_returns_none_for_empty_list(self):
        service = PaaxService()

        trace = service.selected_trace(
            visible_traces=[],
            selected_index=0,
        )

        self.assertIsNone(trace)

    def test_selected_trace_falls_back_to_first_for_bad_index(self):
        service = PaaxService()
        traces = [
            make_trace(name="First"),
            make_trace(name="Second"),
        ]

        trace = service.selected_trace(
            visible_traces=traces,
            selected_index=99,
        )

        self.assertIs(trace, traces[0])

    def test_plot_plan_requires_trace(self):
        service = PaaxService()

        plan = service.plot_plan(trace=None)

        self.assertFalse(plan.ok)
        self.assertEqual(plan.error_title, "No PAAX trace")

    def test_plot_plan_rejects_empty_trace(self):
        service = PaaxService()
        trace = make_trace(x=[], y=[])

        plan = service.plot_plan(trace=trace)

        self.assertFalse(plan.ok)
        self.assertEqual(plan.error_title, "Empty trace")

    def test_plot_plan_rejects_non_finite_trace(self):
        service = PaaxService()
        trace = make_trace(x=[np.nan], y=[np.nan])

        plan = service.plot_plan(trace=trace)

        self.assertFalse(plan.ok)
        self.assertEqual(plan.error_title, "Invalid trace")

    def test_plot_plan_returns_plot_data_for_valid_trace(self):
        service = PaaxService()
        trace = make_trace(study="Study A", name="Current")

        plan = service.plot_plan(
            trace=trace,
            source_path="example.paax",
        )

        self.assertTrue(plan.ok)
        self.assertEqual(plan.name, "Current")
        self.assertEqual(plan.xlabel, "Time (s)")
        self.assertEqual(plan.ylabel, "Current (A)")
        self.assertEqual(plan.x.tolist(), [0.0, 1.0, 2.0])
        self.assertEqual(plan.y.tolist(), [0.1, 0.2, 0.3])
        self.assertEqual(plan.trace_dict["kind"], "paax")
        self.assertIn("Plotted EC trace", plan.status_message)

    def test_finite_ranges(self):
        service = PaaxService()

        x_range, y_range = service.finite_ranges(
            np.asarray([0.0, 1.0, np.nan]),
            np.asarray([5.0, 7.0, np.nan]),
        )

        self.assertEqual(x_range, (0.0, 1.0))
        self.assertEqual(y_range, (5.0, 7.0))


if __name__ == "__main__":
    unittest.main()