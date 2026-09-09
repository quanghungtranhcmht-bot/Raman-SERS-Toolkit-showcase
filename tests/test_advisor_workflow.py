from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ecsers_analyzer.domain.recipe import ProcessingRecipe
from ecsers_analyzer.processing.advisor_workflow import (
    advisor_log_notes,
    advisor_status_applied,
    advisor_status_rejected,
    can_run_advisor,
    clean_advisor_text,
    feature_summary_lines,
    format_advisor_value,
    format_feature_value,
    reason_lines,
    recommendation_dialog_message,
    recipe_summary_lines,
    recipe_ui_values,
)


def make_recipe() -> ProcessingRecipe:
    return ProcessingRecipe(
        despike=True,
        despike_window=7,
        despike_threshold=6.0,
        baseline="airpls",
        baseline_params={
            "lam": 1e5,
            "max_iter": 100,
        },
        smooth_window_points=15,
        smooth_width_cm1=20.0,
        smooth_polyorder=2,
        normalize="max",
        laser_power_mw=34.1,
        integration_time_s=20.0,
    )


def make_recommendation():
    return SimpleNamespace(
        recipe=make_recipe(),
        reasons=[
            "Moderate noise detected; using moderately wider SavGol smoothing.",
            "Plot purpose selected; recommending max normalization for visual comparison.",
        ],
        features={
            "n_points": 1024,
            "noise_relative": 0.052345,
            "baseline_curvature": 0.123456,
            "estimated_spike_count": 2,
        },
    )


class AdvisorWorkflowTests(unittest.TestCase):
    def test_clean_advisor_text(self):
        self.assertEqual(clean_advisor_text("  hello  "), "hello")
        self.assertEqual(clean_advisor_text(None), "")

    def test_can_run_advisor_requires_raw_spectrum(self):
        plan = can_run_advisor(None)

        self.assertFalse(plan.ok)
        self.assertEqual(plan.error_title, "No spectrum")
        self.assertIn("Open a spectrum", plan.error_message)

    def test_can_run_advisor_accepts_raw_spectrum(self):
        plan = can_run_advisor(object())

        self.assertTrue(plan.ok)

    def test_format_advisor_value(self):
        self.assertEqual(format_advisor_value(100000.0), "100000")
        self.assertEqual(format_advisor_value(0.001), "0.001")
        self.assertEqual(format_advisor_value(None), "")

    def test_recipe_ui_values(self):
        values = recipe_ui_values(make_recipe())

        self.assertTrue(values["despike_checked"])
        self.assertEqual(values["despike_window"], "7")
        self.assertEqual(values["despike_threshold"], "6.0")
        self.assertEqual(values["despike_max_width_points"], "1")
        self.assertEqual(values["baseline"], "airpls")
        self.assertEqual(values["lam"], "100000")
        self.assertEqual(values["max_iter"], "100")
        self.assertTrue(values["smooth_checked"])
        self.assertEqual(values["smooth_window_points"], "15")
        self.assertTrue(values["smooth_width_enabled"])
        self.assertEqual(values["smooth_width_cm1"], "20")
        self.assertEqual(values["smooth_polyorder"], "2")
        self.assertEqual(values["normalize"], "max")
        self.assertEqual(values["laser_power_mw"], "34.1")

    def test_recipe_ui_values_handles_no_smooth_width(self):
        recipe = make_recipe()
        recipe.smooth_width_cm1 = None

        values = recipe_ui_values(recipe)

        self.assertFalse(values["smooth_width_enabled"])
        self.assertEqual(values["smooth_width_cm1"], "")

    def test_recipe_summary_lines(self):
        lines = recipe_summary_lines(make_recipe())
        text = "\n".join(lines)

        self.assertIn("Baseline: airpls", text)
        self.assertIn("airPLS λ: 100000", text)
        self.assertIn("Despike: True", text)
        self.assertIn("Normalize: max", text)

    def test_reason_lines(self):
        lines = reason_lines([" reason one ", "", "reason two"])

        self.assertEqual(lines, ["- reason one", "- reason two"])

    def test_reason_lines_empty(self):
        lines = reason_lines([])

        self.assertEqual(lines, ["- No explanation was provided."])

    def test_format_feature_value(self):
        self.assertEqual(format_feature_value(0.0523456), "0.0523456")
        self.assertEqual(format_feature_value(None), "")
        self.assertEqual(format_feature_value("abc"), "abc")

    def test_feature_summary_lines(self):
        lines = feature_summary_lines(
            {
                "n_points": 1024,
                "noise_relative": 0.052345,
                "bad": None,
            }
        )

        self.assertIn("n_points: 1024", lines)
        self.assertIn("noise_relative: 0.052345", lines)
        self.assertNotIn("bad: ", lines)

    def test_recommendation_dialog_message_is_transparent(self):
        message = recommendation_dialog_message(make_recommendation())

        self.assertIn("Recommended processing settings", message)
        self.assertIn("Baseline: airpls", message)
        self.assertIn("Reasons:", message)
        self.assertIn("Moderate noise detected", message)
        self.assertIn("Measured features:", message)
        self.assertIn("noise_relative", message)
        self.assertIn("Apply these settings", message)

    def test_status_messages(self):
        self.assertIn("settings applied", advisor_status_applied())
        self.assertIn("not applied", advisor_status_rejected())

    def test_advisor_log_notes(self):
        notes = advisor_log_notes(make_recommendation(), decision="accepted")

        self.assertIn("decision=accepted", notes)
        self.assertIn("baseline=airpls", notes)
        self.assertIn("lam=100000", notes)
        self.assertIn("despike=True", notes)
        self.assertIn("normalize=max", notes)
        self.assertIn("reasons=", notes)


if __name__ == "__main__":
    unittest.main()