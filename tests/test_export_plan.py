from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ecsers_analyzer.export.plan import (
    batch_export_mode,
    batch_mode_needs_stack_offset,
    current_batch_export_labels,
    default_batch_raman_export_filename,
    default_paax_export_filename,
    default_single_raman_export_filename,
    ensure_file_extension,
    normalize_chart_title_mode,
    optional_text,
    overlay_title_for_batch,
    per_sheet_titles_from_specs,
    reference_subtraction_export_warning_needed,
    safe_excel_sheet_name,
    sanitize_filename_stem,
)


class ExportPlanTests(unittest.TestCase):
    def test_ensure_file_extension_adds_extension(self):
        self.assertEqual(ensure_file_extension("output", ".xlsx"), "output.xlsx")
        self.assertEqual(ensure_file_extension("output.xlsx", ".xlsx"), "output.xlsx")
        self.assertEqual(ensure_file_extension("trace", "csv"), "trace.csv")

    def test_sanitize_filename_stem_replaces_invalid_characters(self):
        self.assertEqual(
            sanitize_filename_stem('Study 1/Trace: A*?', fallback="x"),
            "Study_1_Trace_A",
        )

    def test_default_single_raman_export_filename(self):
        self.assertEqual(
            default_single_raman_export_filename(Path("Q_5E-5M.csv")),
            "Q_5E-5M_processed.xlsx",
        )

        self.assertEqual(
            default_single_raman_export_filename(None),
            "processed_output.xlsx",
        )

    def test_default_batch_raman_export_filename(self):
        self.assertEqual(
            default_batch_raman_export_filename(Path("Batch Folder")),
            "Batch_Folder_batch_processed.xlsx",
        )

        self.assertEqual(
            default_batch_raman_export_filename(None),
            "batch_processed.xlsx",
        )

    def test_default_paax_export_filename(self):
        self.assertEqual(
            default_paax_export_filename("Samp 1", "Current / Time", ".csv"),
            "Samp_1_Current_Time.csv",
        )

        self.assertEqual(
            default_paax_export_filename("Samp 1", "Current / Time", ".xlsx"),
            "Samp_1_Current_Time.xlsx",
        )

    def test_safe_excel_sheet_name_removes_illegal_characters_and_limits_length(self):
        name = safe_excel_sheet_name("bad/name:*?[]" + "x" * 50)

        self.assertLessEqual(len(name), 31)
        for ch in [":", "\\", "/", "?", "*", "[", "]"]:
            self.assertNotIn(ch, name)

    def test_safe_excel_sheet_name_avoids_duplicates(self):
        used = {"sample", "sample_2"}
        self.assertEqual(safe_excel_sheet_name("sample", used=used), "sample_3")

    def test_title_mode_cleanup(self):
        self.assertEqual(normalize_chart_title_mode("custom"), "custom")
        self.assertEqual(normalize_chart_title_mode("SAMPLE"), "sample")
        self.assertEqual(normalize_chart_title_mode("bad"), "blank")

    def test_optional_text(self):
        self.assertIsNone(optional_text(""))
        self.assertIsNone(optional_text("   "))
        self.assertEqual(optional_text(" Intensity "), "Intensity")

    def test_batch_export_mode_falls_back_safely(self):
        self.assertEqual(
            batch_export_mode("single", data_are_reference_subtracted=False),
            "overlay",
        )

        self.assertEqual(
            batch_export_mode("unknown", data_are_reference_subtracted=False),
            "overlay",
        )

        self.assertEqual(
            batch_export_mode("stacked", data_are_reference_subtracted=False),
            "stacked",
        )

    def test_reference_subtracted_mode_requires_actual_subtracted_data(self):
        self.assertEqual(
            batch_export_mode(
                "reference_subtracted_stacked",
                data_are_reference_subtracted=False,
            ),
            "stacked",
        )

        self.assertEqual(
            batch_export_mode(
                "reference_subtracted_stacked",
                data_are_reference_subtracted=True,
            ),
            "reference_subtracted_stacked",
        )

        self.assertTrue(
            reference_subtraction_export_warning_needed(
                "reference_subtracted_stacked",
                data_are_reference_subtracted=False,
            )
        )

    def test_current_batch_export_labels_prefers_trace_labels_when_count_matches(self):
        traces = [
            {"label": "OCP", "role": "processed"},
            {"label": "-0.3 V", "role": "processed"},
        ]

        specs = [
            SimpleNamespace(metadata={"filename_stem": "file1"}),
            SimpleNamespace(metadata={"filename_stem": "file2"}),
        ]

        labels = current_batch_export_labels(
            traces=traces,
            current_plot_mode="stacked",
            batch_specs=specs,
            batch_labels=["old1", "old2"],
        )

        self.assertEqual(labels, ["OCP", "-0.3 V"])

    def test_current_batch_export_labels_falls_back_to_batch_labels(self):
        traces = [{"label": "Only one", "role": "processed"}]

        specs = [
            SimpleNamespace(metadata={"filename_stem": "file1"}),
            SimpleNamespace(metadata={"filename_stem": "file2"}),
        ]

        labels = current_batch_export_labels(
            traces=traces,
            current_plot_mode="stacked",
            batch_specs=specs,
            batch_labels=["batch1", "batch2"],
        )

        self.assertEqual(labels, ["batch1", "batch2"])

    def test_current_batch_export_labels_falls_back_to_metadata(self):
        specs = [
            SimpleNamespace(metadata={"legend_label": "A"}),
            SimpleNamespace(metadata={"filename_stem": "B_file"}),
            SimpleNamespace(metadata={}),
        ]

        labels = current_batch_export_labels(
            traces=[],
            current_plot_mode="overlay",
            batch_specs=specs,
            batch_labels=[],
        )

        self.assertEqual(labels, ["A", "B_file", "Spectrum_3"])

    def test_per_sheet_titles_from_specs(self):
        specs = [
            SimpleNamespace(metadata={"chart_title": "Title 1"}),
            SimpleNamespace(metadata={}),
        ]

        self.assertEqual(per_sheet_titles_from_specs(specs), ["Title 1", ""])

    def test_overlay_title_for_batch(self):
        self.assertEqual(
            overlay_title_for_batch(
                mode="overlay",
                chart_title_mode="sample",
                chart_title_text="",
            ),
            "Overlay",
        )

        self.assertEqual(
            overlay_title_for_batch(
                mode="reference_subtracted_stacked",
                chart_title_mode="sample",
                chart_title_text="",
            ),
            "reference subtracted stacked",
        )

        self.assertEqual(
            overlay_title_for_batch(
                mode="stacked",
                chart_title_mode="custom",
                chart_title_text="My Export",
            ),
            "My Export",
        )

        self.assertIsNone(
            overlay_title_for_batch(
                mode="stacked",
                chart_title_mode="blank",
                chart_title_text="Ignored",
            )
        )

    def test_batch_mode_needs_stack_offset(self):
        self.assertFalse(batch_mode_needs_stack_offset("overlay"))
        self.assertTrue(batch_mode_needs_stack_offset("stacked"))
        self.assertTrue(batch_mode_needs_stack_offset("reference_subtracted_stacked"))


if __name__ == "__main__":
    unittest.main()