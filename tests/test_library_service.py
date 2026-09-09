from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ecsers_analyzer.services.library_service import LibraryService


class DummyHistoryService:
    def __init__(self):
        self.references = []
        self.searches = []

    def log_library_reference_added(self, **kwargs):
        self.references.append(kwargs)
        return True

    def log_library_search(self, **kwargs):
        self.searches.append(kwargs)
        return True



class LibraryServiceTests(unittest.TestCase):
    def test_add_reference_requires_processed_spectrum(self):
        service = LibraryService()

        result = service.add_reference(
            processed_spec=None,
            raw_spec=None,
            source_path=None,
            compound_text="Quercetin",
            concentration_text="5e-5",
            notes_text="standard",
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error_title, "No processed spectrum")

    
    @patch("ecsers_analyzer.services.library_service.add_reference_spectrum")
    def test_add_reference_success(self, mock_add):
        history = DummyHistoryService()
        service = LibraryService(history_service=history)
        processed = object()

        mock_add.return_value = {
            "reference_id": "ref001",
            "compound_name": "Quercetin",
        }

        result = service.add_reference(
            processed_spec=processed,
            raw_spec=None,
            source_path="sample.csv",
            compound_text="Quercetin",
            concentration_text="5e-5",
            notes_text="standard",
        )

        self.assertEqual(len(history.references), 1)
        self.assertTrue(result.ok)
        self.assertEqual(result.compound_name, "Quercetin")
        self.assertIn("Added library reference", result.status_message)
        self.assertIn("Quercetin", result.user_message)

        mock_add.assert_called_once()

    
    @patch("ecsers_analyzer.services.library_service.add_reference_spectrum")
    def test_add_reference_reports_save_failure(self, mock_add):
        service = LibraryService()
        processed = object()

        mock_add.side_effect = RuntimeError("disk error")

        result = service.add_reference(
            processed_spec=processed,
            raw_spec=None,
            source_path="sample.csv",
            compound_text="Quercetin",
            concentration_text="5e-5",
            notes_text="standard",
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error_title, "Library save failed")
        self.assertIn("disk error", result.error_message)

    def test_search_requires_processed_spectrum(self):
        service = LibraryService()

        result = service.search_unknown(
            processed_spec=None,
            raw_spec=None,
            source_path=None,
            xlim=(400, 1700),
            top_n=10,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error_title, "No processed spectrum")

    
    @patch("ecsers_analyzer.services.library_service.search_library")
    def test_search_success(self, mock_search):
        history = DummyHistoryService()
        service = LibraryService(history_service=history)
        processed = object()

        mock_search.return_value = [
            {
                "compound_name": "Quercetin",
                "score": 0.912345,
                "reference_id": "ref001",
            }
        ]

        result = service.search_unknown(
            processed_spec=processed,
            raw_spec=None,
            source_path="unknown.csv",
            xlim=(400, 1700),
            top_n=10,
        )

        self.assertEqual(len(history.searches), 1)
        self.assertTrue(result.ok)
        self.assertEqual(len(result.results), 1)
        self.assertEqual(result.table_rows[0], ["1", "Quercetin", "0.9123", "ref001"])
        self.assertIn("Top candidate library match", result.status_message)

        mock_search.assert_called_once()
        

    @patch("ecsers_analyzer.services.library_service.search_library")
    def test_search_reports_failure(self, mock_search):
        service = LibraryService()
        processed = object()

        mock_search.side_effect = RuntimeError("bad library")

        result = service.search_unknown(
            processed_spec=processed,
            raw_spec=None,
            source_path="unknown.csv",
            xlim=(400, 1700),
            top_n=10,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error_title, "Library search failed")
        self.assertIn("bad library", result.error_message)


if __name__ == "__main__":
    unittest.main()