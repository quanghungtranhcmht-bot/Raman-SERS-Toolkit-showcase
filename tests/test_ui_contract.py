from __future__ import annotations

from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


class UiContractTests(unittest.TestCase):
    def test_spectral_viewer_has_connected_methods(self):
        try:
            from qt_ecsers_ui_dynamic import SpectralViewer
        except Exception as exc:
            self.skipTest(f"Qt UI dependencies not available: {exc}")

        required_methods = [
            # Main workflow slots
            "open_spectrum",
            "run_processing",
            "open_batch_folder",
            "run_batch_plot",
            "open_paax",
            "plot_paax_trace",

            # Export slots
            "export_single_excel",
            "export_batch_excel_qt",
            "export_paax_selected_csv",
            "export_paax_selected_excel",
            "copy_peak_intensity_table",
            "export_peak_intensity_csv",

            # Library slots
            "add_current_to_library",
            "search_current_library",

            # Plot/interaction slots
            "redraw_current_plot",
            "reset_plot_view",
            "autoscale_y",
            "copy_plot_image",
            "save_plot_png",
            "_toggle_focus_plot",
            "_toggle_analysis_panel",
            "_plot_style_changed",
            "_pen_for_trace",

            # Peak/ROI table refresh methods
            "_refresh_trace_table",
            "_refresh_peak_table",
            "_refresh_peak_intensity_table",
            "_refresh_roi_table",

            # Peak/ROI actions
            "_set_peak_pick_mode",
            "add_peak_marker_at_cursor",
            "add_peak_marker_manual",
            "clear_peak_markers",
            "add_roi_from_view",
            "add_roi_manual",
            "clear_region_markers",

            # Tab builder compatibility methods
            "_build_single_tab",
            "_build_ec_tab",
            "_build_processing_tab",
            "_build_batch_tab",
            "_build_plot_tab",
            "_build_export_tab",
            "_build_library_tab",
        ]

        for name in required_methods:
            self.assertTrue(
                hasattr(SpectralViewer, name),
                f"SpectralViewer is missing connected method: {name}",
            )


if __name__ == "__main__":
    unittest.main()