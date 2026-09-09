from __future__ import annotations

from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


class PlotControllerContractTests(unittest.TestCase):
    def test_plot_controller_imports_and_has_expected_methods(self):
        try:
            from ecsers_analyzer.frontend.qt.controllers.plot_controller import PlotController
        except Exception as exc:
            self.skipTest(f"Qt/PyQtGraph dependencies not available: {exc}")

        required_methods = [
            "refresh_trace_table",
            "trace_table_changed",
            "reset_plot",
            "pen_for_trace",
            "redraw_current_plot",
            "reset_plot_view",
            "autoscale_y",
            "copy_plot_image",
            "save_plot_png",
            "toggle_focus_plot",
            "plot_style_changed",
        ]

        for name in required_methods:
            self.assertTrue(
                hasattr(PlotController, name),
                f"PlotController is missing method: {name}",
            )

    def test_spectral_viewer_keeps_plot_delegate_methods(self):
        try:
            from qt_ecsers_ui_dynamic import SpectralViewer
        except Exception as exc:
            self.skipTest(f"Qt UI dependencies not available: {exc}")

        required_methods = [
            "_refresh_trace_table",
            "_trace_table_changed",
            "_reset_plot",
            "redraw_current_plot",
            "_trace_xy",
            "_pen_for_trace",
            "reset_plot_view",
            "autoscale_y",
            "copy_plot_image",
            "save_plot_png",
            "_toggle_focus_plot",
            "_plot_style_changed",
        ]

        for name in required_methods:
            self.assertTrue(
                hasattr(SpectralViewer, name),
                f"SpectralViewer is missing plot delegate method: {name}",
            )


if __name__ == "__main__":
    unittest.main()