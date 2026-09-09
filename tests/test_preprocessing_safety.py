from __future__ import annotations

from pathlib import Path
import sys
import unittest

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ecsers_analyzer.domain.recipe import ProcessingRecipe
from ecsers_analyzer.domain.spectrum import Spectrum
from ecsers_analyzer.processing.pipeline import process_spectrum
from ecsers_analyzer.processing.preprocessing import (
    Preprocessor,
    detect_cosmic_ray_masks,
    window_points_from_cm1,
)


class PreprocessingSafetyTests(unittest.TestCase):
    def _synthetic_trace(self):
        x = np.arange(121, dtype=float)
        rng = np.random.default_rng(123)
        y = 1000.0 + rng.normal(0.0, 2.0, size=x.size)

        # Narrow but real 3-point spectral feature.
        y[49] += 250.0
        y[50] += 600.0
        y[51] += 260.0

        # Isolated positive detector event.
        y[90] += 1200.0
        return x, y

    def test_conservative_detector_preserves_multi_point_peak_and_accepts_isolated_spike(self):
        _, y = self._synthetic_trace()
        candidates, accepted = detect_cosmic_ray_masks(
            y,
            window=7,
            threshold=7.0,
            max_width_points=1,
        )

        self.assertTrue(candidates[49:52].all())
        self.assertFalse(accepted[49:52].any())
        self.assertTrue(candidates[90])
        self.assertTrue(accepted[90])

    def test_despike_interpolates_only_accepted_event(self):
        x, y = self._synthetic_trace()
        prep = Preprocessor(x, y).despike_median(
            window=7,
            threshold=7.0,
            max_width_points=1,
        )

        np.testing.assert_allclose(prep.y[49:52], y[49:52])
        expected = 0.5 * (y[89] + y[91])
        self.assertAlmostEqual(prep.y[90], expected, places=10)
        self.assertEqual(prep.n_spikes_, 1)
        self.assertGreaterEqual(prep.n_spike_candidates_, 4)

    def test_negative_outlier_is_not_removed_as_cosmic_ray(self):
        x = np.arange(41, dtype=float)
        rng = np.random.default_rng(4)
        y = 500.0 + rng.normal(0.0, 1.0, size=x.size)
        y[20] -= 500.0

        prep = Preprocessor(x, y).despike_median(
            window=7,
            threshold=7.0,
            max_width_points=1,
        )

        self.assertEqual(prep.y[20], y[20])
        self.assertFalse(prep.spike_mask_[20])

    def test_cm1_smoothing_no_longer_forces_eleven_point_minimum(self):
        x = np.arange(0.0, 100.0, 2.0)
        self.assertEqual(window_points_from_cm1(x, 8.0), 5)

    def test_processing_records_candidate_and_removed_counts(self):
        x, y = self._synthetic_trace()
        raw = Spectrum(x, y)
        recipe = ProcessingRecipe(
            despike=True,
            despike_window=7,
            despike_threshold=7.0,
            despike_max_width_points=1,
            baseline=None,
            smooth_window_points=0,
            smooth_width_cm1=None,
            normalize=None,
        )

        spec = process_spectrum(raw, recipe)

        self.assertGreaterEqual(spec.n_spike_candidates, 4)
        self.assertEqual(spec.n_spikes_removed, 1)
        self.assertEqual(spec.metadata["n_spikes_removed"], 1)
        self.assertEqual(spec.processing_recipe["despike_params"]["max_width_points"], 1)


if __name__ == "__main__":
    unittest.main()
