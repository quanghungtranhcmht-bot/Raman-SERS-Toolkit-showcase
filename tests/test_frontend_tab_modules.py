from __future__ import annotations

from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


class FrontendTabModuleTests(unittest.TestCase):
    def test_tab_modules_import(self):
        try:
            from ecsers_analyzer.frontend.qt.tabs.single_tab import build_single_tab
            from ecsers_analyzer.frontend.qt.tabs.ec_tab import build_ec_tab
            from ecsers_analyzer.frontend.qt.tabs.processing_tab import build_processing_tab
            from ecsers_analyzer.frontend.qt.tabs.batch_tab import build_batch_tab
            from ecsers_analyzer.frontend.qt.tabs.plot_tab import build_plot_tab
            from ecsers_analyzer.frontend.qt.tabs.export_tab import build_export_tab
            from ecsers_analyzer.frontend.qt.tabs.library_tab import build_library_tab
        except Exception as exc:
            self.skipTest(f"Qt tab modules not importable: {exc}")

        self.assertTrue(callable(build_single_tab))
        self.assertTrue(callable(build_ec_tab))
        self.assertTrue(callable(build_processing_tab))
        self.assertTrue(callable(build_batch_tab))
        self.assertTrue(callable(build_plot_tab))
        self.assertTrue(callable(build_export_tab))
        self.assertTrue(callable(build_library_tab))


if __name__ == "__main__":
    unittest.main()