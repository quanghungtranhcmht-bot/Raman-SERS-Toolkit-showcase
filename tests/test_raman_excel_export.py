from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ecsers_analyzer.domain.spectrum import Spectrum
from ecsers_analyzer.export.raman_excel import (
    export_single_spectrum_excel,
    export_batch_excel,
)


class RamanExcelExportTests(unittest.TestCase):
    def make_spec(self, label="sample"):
        spec = Spectrum(
            np.asarray([400.0, 500.0, 600.0, 700.0]),
            np.asarray([1.0, 2.0, 1.5, 3.0]),
            metadata={
                "filename_stem": label,
                "sample_code": label,
            },
        )
        spec.normalization_method = None
        return spec

    def test_export_single_spectrum_excel_creates_file(self):
        spec = self.make_spec()

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "single.xlsx"

            result_path = export_single_spectrum_excel(
                spec,
                out,
                xlim=(400, 700),
                include_metadata=True,
            )

            self.assertEqual(Path(result_path), out)
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 0)

    def test_spectrum_export_excel_compatibility_method(self):
        spec = self.make_spec()

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "compat.xlsx"

            result_path = spec.export_excel(
                out,
                xlim=(400, 700),
                include_metadata=True,
            )

            self.assertEqual(Path(result_path), out)
            self.assertTrue(out.exists())

    def test_export_batch_excel_creates_file(self):
        specs = [
            self.make_spec("sample_1"),
            self.make_spec("sample_2"),
        ]

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "batch.xlsx"

            result_path = export_batch_excel(
                specs,
                out,
                xlim=(400, 700),
                batch_plot_mode="overlay",
                overlay_labels=["sample 1", "sample 2"],
            )

            self.assertEqual(Path(result_path), out)
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 0)

    def test_export_batch_excel_rejects_empty_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "batch.xlsx"

            with self.assertRaises(ValueError):
                export_batch_excel([], out)


if __name__ == "__main__":
    unittest.main()