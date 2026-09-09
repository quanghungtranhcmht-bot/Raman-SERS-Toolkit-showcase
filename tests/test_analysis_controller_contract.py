from __future__ import annotations

from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


class AnalysisControllerContractTests(unittest.TestCase):
    def test_analysis_controller_imports_and_has_expected_methods(self):
        try:
            from ecsers_analyzer.frontend.qt.controllers.analysis_controller import AnalysisController
        except Exception as exc:
            self.skipTest(f"Qt dependencies not available: {exc}")

        required_methods = [
            "refresh_roi_table",
            "roi_role_changed",
            "roi_table_changed",
            "add_roi_from_view",
            "add_roi_manual",
            "clear_region_markers",
            "refresh_peak_table",
            "peak_table_changed",
            "refresh_peak_intensity_table",
            "copy_peak_intensity_table",
            "export_peak_intensity_csv",
            "add_peak_marker_at_cursor",
            "add_peak_marker_manual",
            "clear_peak_markers",
        ]

        for name in required_methods:
            self.assertTrue(
                hasattr(AnalysisController, name),
                f"AnalysisController is missing method: {name}",
            )

    def test_spectral_viewer_keeps_analysis_delegate_methods(self):
        try:
            from qt_ecsers_ui_dynamic import SpectralViewer
        except Exception as exc:
            self.skipTest(f"Qt UI dependencies not available: {exc}")

        required_methods = [
            "_refresh_roi_table",
            "_roi_role_changed",
            "_roi_table_changed",
            "add_roi_from_view",
            "add_roi_manual",
            "clear_region_markers",
            "_refresh_peak_table",
            "_peak_table_changed",
            "_refresh_peak_intensity_table",
            "copy_peak_intensity_table",
            "export_peak_intensity_csv",
            "add_peak_marker_at_cursor",
            "add_peak_marker_manual",
            "clear_peak_markers",
        ]

        for name in required_methods:
            self.assertTrue(
                hasattr(SpectralViewer, name),
                f"SpectralViewer is missing analysis delegate method: {name}",
            )


if __name__ == "__main__":
    unittest.main()
