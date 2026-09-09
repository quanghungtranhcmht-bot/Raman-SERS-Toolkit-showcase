from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ecsers_analyzer.processing.form import (
    ProcessingFormValues,
    build_baseline_params,
    build_processing_recipe_from_form,
    clean_processing_text,
    integration_time_from_raw_spec,
    parse_float_field,
    parse_int_field,
)


def default_form(**overrides):
    values = dict(
        despike_checked=False,
        despike_window="7",
        despike_threshold="7.0",
        despike_max_width_points="1",
        baseline="airpls",
        lam="100000",
        max_iter="80",
        smooth_checked=False,
        smooth_window_points="5",
        smooth_width_enabled=True,
        smooth_width_cm1="8",
        smooth_polyorder="2",
        normalize="none",
        laser_power_mw="34.1",
    )
    values.update(overrides)
    return ProcessingFormValues(**values)


class ProcessingFormTests(unittest.TestCase):
    def test_clean_processing_text(self):
        self.assertEqual(clean_processing_text("  airpls  "), "airpls")
        self.assertEqual(clean_processing_text(None), "")

    def test_parse_float_field(self):
        value, err = parse_float_field("5e-5", field_name="test")
        self.assertEqual(value, 5e-5)
        self.assertIsNone(err)

        value, err = parse_float_field("bad", field_name="test")
        self.assertIsNone(value)
        self.assertIn("numeric", err)

    def test_parse_int_field_accepts_float_like_text(self):
        value, err = parse_int_field("7.0", field_name="window")
        self.assertEqual(value, 7)
        self.assertIsNone(err)

    def test_baseline_none_has_empty_params(self):
        params, err = build_baseline_params(
            baseline="none",
            lam_text="100000",
            max_iter_text="80",
        )

        self.assertEqual(params, {})
        self.assertIsNone(err)

    def test_airpls_baseline_params(self):
        params, err = build_baseline_params(
            baseline="airpls",
            lam_text="100000",
            max_iter_text="80",
        )

        self.assertIsNone(err)
        self.assertEqual(params["lam"], 100000.0)
        self.assertEqual(params["max_iter"], 80)
        self.assertEqual(params["tol"], 1e-3)
        self.assertEqual(params["w_min"], 1e-6)
        self.assertEqual(params["exp_clip"], 15.0)

    def test_invalid_airpls_lambda_returns_error(self):
        plan = build_processing_recipe_from_form(
            default_form(lam="bad")
        )

        self.assertFalse(plan.ok)
        self.assertEqual(plan.error_title, "Invalid baseline setting")
        self.assertIn("lambda", plan.error_message)

    def test_valid_default_form_creates_recipe(self):
        plan = build_processing_recipe_from_form(default_form())

        self.assertTrue(plan.ok)

        recipe = plan.recipe

        self.assertFalse(recipe.despike)
        self.assertEqual(recipe.despike_window, 7)
        self.assertEqual(recipe.despike_threshold, 7.0)
        self.assertEqual(recipe.despike_max_width_points, 1)
        self.assertEqual(recipe.baseline, "airpls")
        self.assertEqual(recipe.baseline_params["lam"], 100000.0)
        self.assertEqual(recipe.smooth_window_points, 0)
        self.assertIsNone(recipe.smooth_width_cm1)
        self.assertEqual(recipe.smooth_polyorder, 2)
        self.assertIsNone(recipe.normalize)
        self.assertEqual(recipe.laser_power_mw, 34.1)


    def test_disabled_despike_ignores_stale_invalid_fields(self):
        plan = build_processing_recipe_from_form(
            default_form(
                despike_checked=False,
                despike_window="bad",
                despike_threshold="bad",
                despike_max_width_points="bad",
            )
        )

        self.assertTrue(plan.ok)
        self.assertFalse(plan.recipe.despike)
        self.assertEqual(plan.recipe.despike_max_width_points, 1)

    def test_baseline_none_creates_recipe_with_no_baseline(self):
        plan = build_processing_recipe_from_form(
            default_form(baseline="none")
        )

        self.assertTrue(plan.ok)
        self.assertIsNone(plan.recipe.baseline)
        self.assertEqual(plan.recipe.baseline_params, {})

    def test_smoothing_width_disabled_uses_point_window_only(self):
        plan = build_processing_recipe_from_form(
            default_form(smooth_checked=True, smooth_width_enabled=False)
        )

        self.assertTrue(plan.ok)
        self.assertIsNone(plan.recipe.smooth_width_cm1)
        self.assertEqual(plan.recipe.smooth_window_points, 5)

    def test_negative_smoothing_width_returns_error(self):
        plan = build_processing_recipe_from_form(
            default_form(smooth_checked=True, smooth_width_cm1="-18")
        )

        self.assertFalse(plan.ok)
        self.assertEqual(plan.error_title, "Invalid smoothing setting")
        self.assertIn("cm", plan.error_message)

    def test_blank_optional_laser_power_becomes_none_for_non_power_time(self):
        plan = build_processing_recipe_from_form(
            default_form(laser_power_mw="")
        )

        self.assertTrue(plan.ok)
        self.assertIsNone(plan.recipe.laser_power_mw)

    def test_power_time_requires_laser_power(self):
        plan = build_processing_recipe_from_form(
            default_form(normalize="power_time", laser_power_mw="")
        )

        self.assertFalse(plan.ok)
        self.assertEqual(plan.error_title, "Laser power required")

    def test_integration_time_from_raw_spec(self):
        raw = SimpleNamespace(metadata={"integration_time_s": "25"})

        self.assertEqual(integration_time_from_raw_spec(raw), 25.0)

    def test_power_time_uses_metadata_integration_time(self):
        raw = SimpleNamespace(metadata={"integration_time_s": "25"})

        plan = build_processing_recipe_from_form(
            default_form(normalize="power_time"),
            raw_spec=raw,
        )

        self.assertTrue(plan.ok)
        self.assertEqual(plan.recipe.normalize, "power_time")
        self.assertEqual(plan.recipe.integration_time_s, 25.0)

    def test_power_time_requests_acquisition_time_when_missing(self):
        raw = SimpleNamespace(metadata={})

        plan = build_processing_recipe_from_form(
            default_form(normalize="power_time"),
            raw_spec=raw,
        )

        self.assertFalse(plan.ok)
        self.assertTrue(plan.needs_acquisition_time)
        self.assertEqual(plan.error_title, "Acquisition time required")

    def test_power_time_accepts_provided_acquisition_time(self):
        raw = SimpleNamespace(metadata={})

        plan = build_processing_recipe_from_form(
            default_form(normalize="power_time"),
            raw_spec=raw,
            provided_integration_time_s=20.0,
        )

        self.assertTrue(plan.ok)
        self.assertEqual(plan.recipe.integration_time_s, 20.0)


if __name__ == "__main__":
    unittest.main()