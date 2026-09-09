from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ecsers_analyzer.io.csv_loader import load_csv_spectrum

REAL_CSV_PATH = os.environ.get("EC_SERS_REAL_CSV", "")


@unittest.skipUnless(REAL_CSV_PATH, "Set EC_SERS_REAL_CSV to run this optional real CSV smoke test.")
class RealCsvSmokeTests(unittest.TestCase):
    def test_load_and_process_real_csv(self):
        spec = load_csv_spectrum(REAL_CSV_PATH, laser_power_mw=34.1)
        spec.preprocess(
            baseline="airpls",
            baseline_params=dict(lam=1e5, max_iter=80, tol=1e-3, w_min=1e-6, exp_clip=15.0),
            smooth_window=15,
            normalize="power_time",
        )
        self.assertEqual(len(spec.x), len(spec.y))


if __name__ == "__main__":
    unittest.main()
