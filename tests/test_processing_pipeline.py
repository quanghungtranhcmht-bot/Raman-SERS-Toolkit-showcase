from __future__ import annotations

from pathlib import Path
import sys
import unittest

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ecsers_analyzer.domain.spectrum import Spectrum
from ecsers_analyzer.domain.recipe import ProcessingRecipe
from ecsers_analyzer.processing.pipeline import process_spectrum


class ProcessingPipelineTests(unittest.TestCase):
    def test_synthetic_spectrum_processing_preserves_traceability(self):
        x = np.linspace(400, 1700, 1000)
        baseline = 1000 + 0.2 * (x - 400)
        peak1 = 500 * np.exp(-0.5 * ((x - 1000) / 12) ** 2)
        peak2 = 800 * np.exp(-0.5 * ((x - 1590) / 10) ** 2)
        noise = np.random.default_rng(1).normal(0, 20, size=x.size)
        y = baseline + peak1 + peak2 + noise
        y[300] += 2000

        raw = Spectrum(x, y, metadata={"laser_power_mw": 34.1, "integration_time_s": 20})
        recipe = ProcessingRecipe(
            despike=True,
            despike_window=7,
            despike_threshold=6.0,
            baseline="airpls",
            baseline_params={
                "lam": 1e5,
                "max_iter": 80,
                "tol": 1e-3,
                "w_min": 1e-6,
                "exp_clip": 15.0,
            },
            smooth_width_cm1=18.0,
            smooth_window_points=15,
            smooth_polyorder=2,
            normalize=None,
            laser_power_mw=34.1,
        )

        spec = process_spectrum(raw, recipe, label="synthetic")

        self.assertEqual(spec.x.size, spec.y.size)
        self.assertTrue(np.isfinite(spec.x).all())
        self.assertTrue(np.isfinite(spec.y).all())
        self.assertIsNotNone(getattr(spec, "baseline", None))
        self.assertIsNotNone(getattr(spec, "y_bc", None))
        self.assertIsNotNone(getattr(spec, "processing_recipe", None))
        self.assertIs(getattr(spec, "processing_recipe_object", None), recipe)
        self.assertEqual(spec.metadata.get("legend_label"), "synthetic")
        self.assertIn("final_smooth_window_points", spec.processing_recipe)


if __name__ == "__main__":
    unittest.main()
