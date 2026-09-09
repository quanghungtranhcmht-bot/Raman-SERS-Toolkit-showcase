from __future__ import annotations

from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ecsers_analyzer.library.workflow import (
    add_reference_kwargs,
    add_reference_log_notes,
    added_reference_message,
    added_reference_status,
    best_match_summary,
    build_reference_input_plan,
    can_search_library,
    clean_library_text,
    format_score,
    parse_optional_concentration,
    reference_display_label,
    search_result_table_rows,
    search_result_table_values,
    search_status_message,
)


class LibraryWorkflowTests(unittest.TestCase):
    def test_clean_library_text(self):
        self.assertEqual(clean_library_text("  Quercetin  "), "Quercetin")
        self.assertEqual(clean_library_text(None), "")

    def test_parse_optional_concentration_allows_blank(self):
        concentration, err = parse_optional_concentration("")
        self.assertIsNone(concentration)
        self.assertIsNone(err)

    def test_parse_optional_concentration_numeric(self):
        concentration, err = parse_optional_concentration("5e-5")
        self.assertEqual(concentration, 5e-5)
        self.assertIsNone(err)

    def test_parse_optional_concentration_rejects_bad_value(self):
        concentration, err = parse_optional_concentration("abc")
        self.assertIsNone(concentration)
        self.assertIn("numeric", err)

    def test_parse_optional_concentration_rejects_negative(self):
        concentration, err = parse_optional_concentration("-1")
        self.assertIsNone(concentration)
        self.assertIn("negative", err)

    def test_build_reference_input_plan_requires_processed_spectrum(self):
        plan = build_reference_input_plan(
            processed_spec=None,
            compound_text="Quercetin",
            concentration_text="5e-5",
            notes_text="standard",
        )

        self.assertFalse(plan.ok)
        self.assertEqual(plan.error_title, "No processed spectrum")

    def test_build_reference_input_plan_requires_compound(self):
        plan = build_reference_input_plan(
            processed_spec=object(),
            compound_text="  ",
            concentration_text="5e-5",
            notes_text="standard",
        )

        self.assertFalse(plan.ok)
        self.assertEqual(plan.error_title, "Missing compound name")

    def test_build_reference_input_plan_accepts_valid_input(self):
        plan = build_reference_input_plan(
            processed_spec=object(),
            compound_text=" Quercetin ",
            concentration_text="5e-5",
            notes_text="  reference standard  ",
        )

        self.assertTrue(plan.ok)
        self.assertEqual(plan.compound_name, "Quercetin")
        self.assertEqual(plan.concentration_M, 5e-5)
        self.assertEqual(plan.notes, "reference standard")

    def test_add_reference_kwargs(self):
        plan = build_reference_input_plan(
            processed_spec=object(),
            compound_text="Rutin",
            concentration_text="1e-4",
            notes_text="good reference",
        )

        kwargs = add_reference_kwargs(plan)

        self.assertEqual(kwargs["compound_name"], "Rutin")
        self.assertEqual(kwargs["concentration_M"], 1e-4)
        self.assertEqual(kwargs["notes"], "good reference")

    def test_add_reference_status_and_message(self):
        row = {"reference_id": "abc123"}

        self.assertEqual(
            added_reference_status(row, "Quercetin"),
            "Added library reference: Quercetin (abc123)",
        )

        self.assertEqual(
            added_reference_message("Quercetin"),
            "Added Quercetin to the SERS library.",
        )

    def test_add_reference_log_notes(self):
        plan = build_reference_input_plan(
            processed_spec=object(),
            compound_text="Gallic acid",
            concentration_text="5e-5",
            notes_text="",
        )

        self.assertEqual(
            add_reference_log_notes(plan),
            "compound=Gallic acid; concentration_M=5e-05",
        )

    def test_can_search_library_requires_processed_spectrum(self):
        ok, title, message = can_search_library(None)

        self.assertFalse(ok)
        self.assertEqual(title, "No processed spectrum")
        self.assertIn("unknown spectrum", message)

    def test_format_score(self):
        self.assertEqual(format_score(0.987654, digits=3), "0.988")
        self.assertEqual(format_score("bad"), "")

    def test_search_result_table_values(self):
        result = {
            "compound_name": "Quercetin",
            "score": 0.912345,
            "reference_id": "ref001",
        }

        row = search_result_table_values(result, rank=1)

        self.assertEqual(row, ["1", "Quercetin", "0.9123", "ref001"])

    def test_search_result_table_rows(self):
        results = [
            {
                "compound_name": "Quercetin",
                "score": 0.91,
                "reference_id": "ref001",
            },
            {
                "compound_name": "Rutin",
                "score": 0.82,
                "reference_id": "ref002",
            },
        ]

        rows = search_result_table_rows(results)

        self.assertEqual(rows[0], ["1", "Quercetin", "0.9100", "ref001"])
        self.assertEqual(rows[1], ["2", "Rutin", "0.8200", "ref002"])

    def test_search_status_message_uses_candidate_language(self):
        results = [
            {
                "compound_name": "Quercetin",
                "score": 0.912345,
                "reference_id": "ref001",
            }
        ]

        message = search_status_message(results)

        self.assertIn("Top candidate library match", message)
        self.assertIn("Quercetin", message)
        self.assertIn("0.912", message)

    def test_search_status_message_empty(self):
        self.assertEqual(
            search_status_message([]),
            "No library matches found.",
        )

    def test_best_match_summary_uses_not_definitive_language(self):
        results = [
            {
                "compound_name": "Quercetin",
                "score": 0.912345,
                "cosine": 0.93,
                "pearson": 0.89,
                "reference_id": "ref001",
            }
        ]

        summary = best_match_summary(results)

        self.assertIn("Best candidate reference match", summary)
        self.assertIn("Quercetin", summary)
        self.assertIn("not definitive identification", summary)

    def test_reference_display_label(self):
        row = {
            "compound_name": "Catechin",
            "concentration_M": 5e-5,
            "reference_id": "ref003",
        }

        self.assertEqual(
            reference_display_label(row),
            "Catechin, 5e-05 M [ref003]",
        )


if __name__ == "__main__":
    unittest.main()