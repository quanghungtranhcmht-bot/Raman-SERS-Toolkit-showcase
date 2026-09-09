from __future__ import annotations

from pathlib import Path
import sys
import unittest

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ecsers_analyzer.io.vendor_importers import load_spe_spectrum, load_paax_traces, find_traces

EXAMPLES = PROJECT_ROOT / "examples"
SPE = EXAMPLES / "spectra" / "AgNPs_29x_OCP_785nm_50x_20s_samp1.spe"
PAAX = EXAMPLES / "electrochemistry" / "Session Data [2026-JUN-01 1216 #1].paax"


class VendorImporterTests(unittest.TestCase):

    @unittest.skipUnless(SPE.exists(), "Optional local SPE example not available")
    def test_load_example_spe(self):
        spec = load_spe_spectrum(SPE, laser_power_mw=34.1)

        self.assertEqual(len(spec.x), len(spec.y))
        self.assertEqual(len(spec.x), 1024)
        self.assertEqual(spec.metadata.get("x_kind"), "raman_shift_cm-1")
        self.assertTrue(np.isfinite(spec.x).all())
        self.assertTrue(np.isfinite(spec.y).all())
        self.assertGreater(float(spec.x.max()), float(spec.x.min()))

    @unittest.skipUnless(PAAX.exists(), "Optional local PAAX example not available")
    def test_load_example_paax(self):
        traces = load_paax_traces(PAAX)

        self.assertGreater(len(traces), 0)
        current = find_traces(traces, name_contains="Current vs Time")
        potential = find_traces(traces, name_contains="Potential vs Time")
        self.assertTrue(current)
        self.assertTrue(potential)
        self.assertTrue(all(len(tr.x) == len(tr.y) for tr in traces[:10]))


if __name__ == "__main__":
    unittest.main()
