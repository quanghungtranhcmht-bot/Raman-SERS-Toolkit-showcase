from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ecsers_analyzer.services.history_service import HistoryService


class HistoryServiceTests(unittest.TestCase):
    @patch("ecsers_analyzer.services.history_service.log_processing_event")
    def test_log_single_processed(self, mock_log):
        service = HistoryService()

        ok = service.log_single_processed(
            source_path="sample.csv",
            raw_spec=object(),
            processed_spec=object(),
        )

        self.assertTrue(ok)
        mock_log.assert_called_once()
        self.assertEqual(mock_log.call_args.kwargs["action"], "single_processed")

    @patch("ecsers_analyzer.services.history_service.log_processing_event")
    def test_log_batch_processed(self, mock_log):
        service = HistoryService()

        ok = service.log_batch_processed(
            source_path="sample.csv",
            processed_spec=object(),
            notes="mode=overlay",
        )

        self.assertTrue(ok)
        self.assertEqual(mock_log.call_args.kwargs["action"], "batch_processed")
        self.assertEqual(mock_log.call_args.kwargs["notes"], "mode=overlay")

    @patch("ecsers_analyzer.services.history_service.log_processing_event")
    def test_log_export_single_excel(self, mock_log):
        service = HistoryService()

        ok = service.log_export_single_excel(
            source_path="sample.csv",
            raw_spec=object(),
            processed_spec=object(),
        )

        self.assertTrue(ok)
        self.assertEqual(mock_log.call_args.kwargs["action"], "export_single_excel")

    @patch("ecsers_analyzer.services.history_service.log_processing_event")
    def test_log_export_batch_excel(self, mock_log):
        service = HistoryService()

        ok = service.log_export_batch_excel(
            source_path="sample.csv",
            processed_spec=object(),
        )

        self.assertTrue(ok)
        self.assertEqual(mock_log.call_args.kwargs["action"], "export_batch_excel")

    @patch("ecsers_analyzer.services.history_service.log_processing_event")
    def test_log_advisor_accepted(self, mock_log):
        service = HistoryService()

        ok = service.log_advisor_decision(
            decision="accepted",
            source_path="sample.csv",
            raw_spec=object(),
            processed_spec=object(),
            recipe=object(),
            notes="advisor notes",
        )

        self.assertTrue(ok)
        self.assertEqual(mock_log.call_args.kwargs["action"], "advisor_accepted")
        self.assertEqual(mock_log.call_args.kwargs["notes"], "advisor notes")

    @patch("ecsers_analyzer.services.history_service.log_processing_event")
    def test_log_advisor_rejected(self, mock_log):
        service = HistoryService()

        ok = service.log_advisor_decision(
            decision="rejected",
            source_path="sample.csv",
            raw_spec=object(),
            processed_spec=object(),
            recipe=object(),
        )

        self.assertTrue(ok)
        self.assertEqual(mock_log.call_args.kwargs["action"], "advisor_rejected")

    @patch("ecsers_analyzer.services.history_service.log_processing_event")
    def test_log_library_reference_added(self, mock_log):
        service = HistoryService()

        ok = service.log_library_reference_added(
            source_path="sample.csv",
            raw_spec=object(),
            processed_spec=object(),
            notes="compound=Quercetin",
        )

        self.assertTrue(ok)
        self.assertEqual(mock_log.call_args.kwargs["action"], "library_reference_added")

    @patch("ecsers_analyzer.services.history_service.log_processing_event")
    def test_log_library_search(self, mock_log):
        service = HistoryService()

        ok = service.log_library_search(
            source_path="unknown.csv",
            raw_spec=object(),
            processed_spec=object(),
            notes="top_n=10",
        )

        self.assertTrue(ok)
        self.assertEqual(mock_log.call_args.kwargs["action"], "library_search")

    @patch("ecsers_analyzer.services.history_service.log_processing_event")
    def test_logging_failure_is_swallowed(self, mock_log):
        service = HistoryService()
        mock_log.side_effect = RuntimeError("disk error")

        ok = service.log_single_processed(
            source_path="sample.csv",
            raw_spec=object(),
            processed_spec=object(),
        )

        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()