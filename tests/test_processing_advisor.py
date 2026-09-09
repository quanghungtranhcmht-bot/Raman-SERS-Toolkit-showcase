from __future__ import annotations

from pathlib import Path
import sys
import unittest

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ecsers_analyzer.domain.spectrum import Spectrum
from ecsers_analyzer.processing.advisor import recommend_recipe


class ProcessingAdvisorTests(unittest.TestCase):
    def test_advisor_returns_transparent_recipe_and_reasons(self):
        x = np.linspace(400, 1700, 1000)
        baseline = 1000 + 0.2 * (x - 400)
        peak = 800 * np.exp(-0.5 * ((x - 1590) / 10) ** 2)
        noise = np.random.default_rng(1).normal(0, 25, size=x.size)
        y = baseline + peak + noise
        y[300] += 1500

        raw = Spectrum(x, y, metadata={"laser_power_mw": 34.1})
        rec = recommend_recipe(raw)

        self.assertEqual(rec.recipe.baseline, "airpls")
        self.assertTrue(rec.recipe.despike)
        self.assertEqual(rec.recipe.despike_max_width_points, 1)
        self.assertIsNone(rec.recipe.smooth_width_cm1)
        self.assertEqual(rec.recipe.smooth_window_points, 0)
        self.assertEqual(rec.recipe.smooth_polyorder, 2)
        self.assertGreater(len(rec.reasons), 0)
        self.assertIsInstance(rec.features, dict)


if __name__ == "__main__":
    unittest.main()
