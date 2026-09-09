from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ecsers_analyzer.services.import_service import DEFAULT_LASER_POWER_MW, ImportService


class ImportServiceTests(unittest.TestCase):
    def test_discover_spectral_files_ignores_metadata_csv(self):
        service = ImportService()

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "sample.csv").write_text("x,y\n1,2\n", encoding="utf-8")
            (folder / "metadata.csv").write_text("ignore,this\n", encoding="utf-8")
            (folder / "sample.spe").write_bytes(b"fake")
            (folder / "notes.txt").write_text("ignore", encoding="utf-8")

            files = service.discover_spectral_files(folder)
            names = [p.name for p in files]

        self.assertEqual(names, ["sample.csv", "sample.spe"])

    def test_discover_spectral_files_recurses_when_no_direct_files(self):
        service = ImportService()

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            sub = folder / "nested"
            sub.mkdir()
            (sub / "sample.csv").write_text("x,y\n1,2\n", encoding="utf-8")

            files = service.discover_spectral_files(folder)

        self.assertEqual([p.name for p in files], ["sample.csv"])

    def test_display_name_relative_to_base_folder(self):
        service = ImportService()

        base = Path("batch")
        path = base / "sub" / "sample.csv"

        self.assertEqual(
            service.display_name(path, base_folder=base),
            str(Path("sub") / "sample.csv"),
        )

    def test_display_name_falls_back_to_filename(self):
        service = ImportService()

        self.assertEqual(
            service.display_name(Path("other") / "sample.csv", base_folder=Path("batch")),
            "sample.csv",
        )

    @patch("ecsers_analyzer.services.import_service.load_csv_spectrum")
    def test_load_csv_spectrum_file(self, mock_csv):
        service = ImportService()
        mock_csv.return_value = object()

        result = service.load_spectrum_file(
            "sample.csv",
            laser_power_mw=34.1,
        )

        self.assertTrue(result.ok)
        self.assertIsNotNone(result.spectrum)
        mock_csv.assert_called_once_with("sample.csv", laser_power_mw=34.1)

    @patch("ecsers_analyzer.services.import_service.load_spe_spectrum")
    def test_load_spe_spectrum_file(self, mock_spe):
        service = ImportService()
        mock_spe.return_value = object()

        result = service.load_spectrum_file(
            "sample.spe",
            laser_power_mw=34.1,
        )

        self.assertTrue(result.ok)
        self.assertIsNotNone(result.spectrum)
        mock_spe.assert_called_once_with("sample.spe", laser_power_mw=34.1)


    def test_load_csv_without_laser_power_uses_default_and_sets_metadata(self):
        service = ImportService()

        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "Q_5E-5M_AgNO3_1E-1M_785nm_50x_25s.csv"
            csv_path.write_text(
                "Raman Shift,Intensity\n400,10\n500,20\n600,15\n",
                encoding="utf-8",
            )

            result = service.load_spectrum_file(csv_path)

        self.assertTrue(result.ok, result.error_message)
        self.assertIsNotNone(result.spectrum)
        self.assertEqual(
            result.spectrum.metadata["laser_power_mw"],
            DEFAULT_LASER_POWER_MW,
        )

    @patch("ecsers_analyzer.services.import_service.load_spe_spectrum")
    def test_load_spe_without_laser_power_passes_default(self, mock_spe):
        service = ImportService()
        mock_spe.return_value = object()

        result = service.load_spectrum_file("sample.spe")

        self.assertTrue(result.ok)
        mock_spe.assert_called_once_with(
            "sample.spe",
            laser_power_mw=DEFAULT_LASER_POWER_MW,
        )

    def test_load_spectrum_file_rejects_unsupported_extension(self):
        service = ImportService()

        result = service.load_spectrum_file("sample.txt")

        self.assertFalse(result.ok)
        self.assertEqual(result.error_title, "Unsupported file")

    @patch("ecsers_analyzer.services.import_service.load_paax_traces")
    def test_load_paax_file_success(self, mock_paax):
        service = ImportService()
        mock_paax.return_value = [object(), object()]

        result = service.load_paax_file("example.paax")

        self.assertTrue(result.ok)
        self.assertEqual(len(result.traces), 2)
        mock_paax.assert_called_once()

    @patch("ecsers_analyzer.services.import_service.load_paax_traces")
    def test_load_paax_file_empty(self, mock_paax):
        service = ImportService()
        mock_paax.return_value = []

        result = service.load_paax_file("example.paax")

        self.assertFalse(result.ok)
        self.assertEqual(result.error_title, "No traces found")


if __name__ == "__main__":
    unittest.main()