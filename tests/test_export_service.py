from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ecsers_analyzer.services.export_service import ExportService


class DummyHistoryService:
    def __init__(self):
        self.single_exports = []
        self.batch_exports = []

    def log_export_single_excel(self, **kwargs):
        self.single_exports.append(kwargs)
        return True

    def log_export_batch_excel(self, **kwargs):
        self.batch_exports.append(kwargs)
        return True
   

class DummyProcessedSpec:
    def __init__(self):
        self.calls = []

    def export_excel(self, out_path, **kwargs):
        self.calls.append((out_path, kwargs))
        Path(out_path).write_text("dummy", encoding="utf-8")


class ExportServiceTests(unittest.TestCase):
    def test_export_single_requires_processed_spectrum(self):
        service = ExportService()

        result = service.export_single_raman(
            processed_spec=None,
            out_path="out.xlsx",
        )

       
        self.assertFalse(result.ok)
        self.assertEqual(result.error_title, "Nothing to export")

    @patch("ecsers_analyzer.services.export_service.export_single_spectrum_excel")
    def test_export_single_success(self, mock_export_single):
        history = DummyHistoryService()
        service = ExportService(history_service=history)
        spec = object()

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "single.xlsx"

            result = service.export_single_raman(
                processed_spec=spec,
                out_path=out,
                xlim=(400, 1700),
                include_metadata=True,
            )

            self.assertEqual(len(history.single_exports), 1)
            self.assertTrue(result.ok)
            mock_export_single.assert_called_once()

    def test_export_batch_requires_specs(self):
        service = ExportService()

        result = service.export_batch_raman(
            batch_specs=[],
            out_path="batch.xlsx",
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error_title, "Nothing to export")

    @patch("ecsers_analyzer.services.export_service.export_batch_excel")
    def test_export_batch_success(self, mock_export):
        history = DummyHistoryService()
        service = ExportService(history_service=history)

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "batch.xlsx"

            result = service.export_batch_raman(
                batch_specs=[object(), object()],
                processed_files=[Path("a.csv"), Path("b.csv")],
                out_path=out,
                xlim=(400, 1700),
                batch_plot_mode="stacked",
                stack_offset=10.0,
            )

        self.assertEqual(len(history.batch_exports), 2)
        self.assertTrue(result.ok)
        mock_export.assert_called_once()

    @patch("ecsers_analyzer.services.export_service.export_paax_trace_csv")
    def test_export_paax_csv_success(self, mock_csv):
        service = ExportService()

        result = service.export_paax_csv(
            trace=object(),
            out_path="trace.csv",
        )

        self.assertTrue(result.ok)
        mock_csv.assert_called_once()

    def test_export_paax_csv_requires_trace(self):
        service = ExportService()

        result = service.export_paax_csv(
            trace=None,
            out_path="trace.csv",
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error_title, "No PAAX trace")

    @patch("ecsers_analyzer.services.export_service.export_paax_trace_excel")
    def test_export_paax_excel_success(self, mock_excel):
        service = ExportService()

        result = service.export_paax_excel(
            trace=object(),
            out_path="trace.xlsx",
            source_path="example.paax",
        )

        self.assertTrue(result.ok)
        mock_excel.assert_called_once()

    @patch("ecsers_analyzer.services.export_service.export_paax_trace_excel")
    def test_export_paax_excel_missing_dependency(self, mock_excel):
        service = ExportService()
        mock_excel.side_effect = ImportError("missing xlsxwriter")

        result = service.export_paax_excel(
            trace=object(),
            out_path="trace.xlsx",
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error_title, "Missing dependency")


if __name__ == "__main__":
    unittest.main()