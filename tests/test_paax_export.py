from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import csv
import sys
import tempfile
import unittest

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ecsers_analyzer.export.paax_export import (
    export_paax_trace_csv,
    export_paax_trace_excel,
)


def make_trace():
    return SimpleNamespace(
        name="Current vs Time",
        xlabel="Time (s)",
        ylabel="Current (A)",
        x=np.asarray([0.0, 1.0, 2.0], dtype=float),
        y=np.asarray([0.1, 0.2, 0.3], dtype=float),
        metadata={
            "study_name": "Samp 1",
            "instrument": "WaveNow",
        },
    )


class PaaxExportTests(unittest.TestCase):
    def test_export_paax_trace_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "trace.csv"

            export_paax_trace_csv(make_trace(), out)

            with open(out, newline="", encoding="utf-8") as f:
                rows = list(csv.reader(f))

        self.assertEqual(rows[0], ["Time (s)", "Current (A)"])
        self.assertEqual(rows[1], ["0.0", "0.1"])
        self.assertEqual(rows[3], ["2.0", "0.3"])

    def test_export_paax_trace_excel_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "trace.xlsx"

            export_paax_trace_excel(
                make_trace(),
                out,
                source_path="example.paax",
            )

            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 0)

    def test_export_paax_trace_excel_rejects_empty_finite_data(self):
        trace = make_trace()
        trace.x = np.asarray([np.nan])
        trace.y = np.asarray([np.nan])

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "trace.xlsx"

            with self.assertRaises(ValueError):
                export_paax_trace_excel(trace, out)


if __name__ == "__main__":
    unittest.main()