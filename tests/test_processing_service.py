from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ecsers_analyzer.domain.recipe import ProcessingRecipe
from ecsers_analyzer.processing.form import ProcessingFormValues
from ecsers_analyzer.services.processing_service import ProcessingService


def default_form(**overrides):
    values = dict(
        despike_checked=False,
        despike_window="7",
        despike_threshold="7.0",
        despike_max_width_points="1",
        baseline="none",
        lam="100000",
        max_iter="80",
        smooth_checked=False,
        smooth_window_points="5",
        smooth_width_enabled=False,
        smooth_width_cm1="8",
        smooth_polyorder="2",
        normalize="none",
        laser_power_mw="",
    )
    values.update(overrides)
    return ProcessingFormValues(**values)


class ProcessingServiceTests(unittest.TestCase):
    def test_build_recipe_from_form_success(self):
        service = ProcessingService()

        plan = service.build_recipe_from_form(default_form())

        self.assertTrue(plan.ok)
        self.assertIsNotNone(plan.recipe)
        self.assertIsNone(plan.recipe.baseline)
        self.assertIsNone(plan.recipe.normalize)

    def test_build_recipe_from_form_error(self):
        service = ProcessingService()

        plan = service.build_recipe_from_form(
            default_form(smooth_checked=True, smooth_width_enabled=True, smooth_width_cm1="-1")
        )

        self.assertFalse(plan.ok)
        self.assertEqual(plan.error_title, "Invalid smoothing setting")

    def test_process_single_requires_raw_spectrum(self):
        service = ProcessingService()

        result = service.process_single(
            raw_spec=None,
            recipe=ProcessingRecipe(),
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error_title, "No spectrum")

    @patch("ecsers_analyzer.services.processing_service.process_spectrum")
    def test_process_single_success(self, mock_process):
        service = ProcessingService()
        raw = object()
        processed = object()
        recipe = ProcessingRecipe()

        mock_process.return_value = processed

        result = service.process_single(
            raw_spec=raw,
            recipe=recipe,
        )

        self.assertTrue(result.ok)
        self.assertIs(result.processed_spec, processed)
        mock_process.assert_called_once_with(raw, recipe)

    @patch("ecsers_analyzer.services.processing_service.process_spectrum")
    def test_process_single_reports_failure(self, mock_process):
        service = ProcessingService()
        raw = object()
        recipe = ProcessingRecipe()

        mock_process.side_effect = RuntimeError("bad smoothing")

        result = service.process_single(
            raw_spec=raw,
            recipe=recipe,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error_title, "Processing failed")
        self.assertIn("bad smoothing", result.error_message)

    def test_recommend_processing_requires_raw_spectrum(self):
        service = ProcessingService()

        result = service.recommend_processing(raw_spec=None)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_title, "No spectrum")

    @patch("ecsers_analyzer.services.processing_service.recommend_recipe")
    def test_recommend_processing_success(self, mock_recommend):
        service = ProcessingService()
        raw = object()
        recommendation = object()

        mock_recommend.return_value = recommendation

        result = service.recommend_processing(
            raw_spec=raw,
            purpose="plot",
        )

        self.assertTrue(result.ok)
        self.assertIs(result.recommendation, recommendation)
        mock_recommend.assert_called_once_with(raw, purpose="plot")

    @patch("ecsers_analyzer.services.processing_service.recommend_recipe")
    def test_recommend_processing_reports_failure(self, mock_recommend):
        service = ProcessingService()
        raw = object()

        mock_recommend.side_effect = RuntimeError("advisor error")

        result = service.recommend_processing(raw_spec=raw)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_title, "Recommendation failed")
        self.assertIn("advisor error", result.error_message)


if __name__ == "__main__":
    unittest.main()