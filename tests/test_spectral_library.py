from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ecsers_analyzer.domain.spectrum import Spectrum
from ecsers_analyzer.library.spectral_library import add_reference_spectrum, list_references, load_reference_arrays
from ecsers_analyzer.library.search import search_library


class SpectralLibraryTests(unittest.TestCase):
    def test_add_and_search_reference_library(self):
        with tempfile.TemporaryDirectory() as tmp:
            test_library = Path(tmp) / "spectral_library"
            x = np.linspace(400, 1700, 1000)

            q_peak = 800 * np.exp(-0.5 * ((x - 1590) / 10) ** 2)
            r_peak = 800 * np.exp(-0.5 * ((x - 1450) / 10) ** 2)

            q = Spectrum(x, q_peak, metadata={"compound": "Quercetin"})
            r = Spectrum(x, r_peak, metadata={"compound": "Rutin"})

            add_reference_spectrum(q, compound_name="Quercetin", library_dir=test_library)
            add_reference_spectrum(r, compound_name="Rutin", library_dir=test_library)

            refs = list_references(test_library)
            self.assertEqual(len(refs), 2)
            arr = load_reference_arrays(refs[0], test_library)
            self.assertIn("y_processed", arr)

            query = Spectrum(x, q_peak + np.random.default_rng(1).normal(0, 5, size=x.size))
            results = search_library(query, library_dir=test_library, top_n=2)

            self.assertTrue(results)
            self.assertEqual(results[0]["compound_name"], "Quercetin")
            self.assertGreater(results[0]["score"], results[1]["score"])


if __name__ == "__main__":
    unittest.main()
