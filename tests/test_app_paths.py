from __future__ import annotations

import importlib
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


class AppPathTests(unittest.TestCase):
    def _load_default_app_paths(self):
        with patch.dict(
            os.environ,
            {
                "ECSERS_DATA_DIR": "",
                "ECSERS_HISTORY_PATH": "",
                "ECSERS_LIBRARY_DIR": "",
            },
            clear=False,
        ):
            import ecsers_analyzer.persistence.app_paths as app_paths
            return importlib.reload(app_paths)

    def test_default_history_path_is_project_data_not_persistence_data(self):
        app_paths = self._load_default_app_paths()

        persistence_dir = PROJECT_ROOT / "ecsers_analyzer" / "persistence"
        history_path = app_paths.DEFAULT_HISTORY_PATH

        self.assertFalse(history_path.is_relative_to(persistence_dir))
        self.assertEqual(
            history_path,
            PROJECT_ROOT / "data" / "user_history" / "processing_runs.jsonl",
        )
        self.assertEqual(
            history_path.parts[-3:],
            ("data", "user_history", "processing_runs.jsonl"),
        )

    def test_default_library_dir_is_project_data_not_persistence_data(self):
        app_paths = self._load_default_app_paths()

        persistence_dir = PROJECT_ROOT / "ecsers_analyzer" / "persistence"
        library_dir = app_paths.DEFAULT_LIBRARY_DIR

        self.assertFalse(library_dir.is_relative_to(persistence_dir))
        self.assertEqual(
            library_dir,
            PROJECT_ROOT / "data" / "spectral_library",
        )
        self.assertEqual(
            library_dir.parts[-2:],
            ("data", "spectral_library"),
        )


if __name__ == "__main__":
    unittest.main()
