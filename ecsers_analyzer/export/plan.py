from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable
import re


VALID_TITLE_MODES = {"blank", "sample", "custom"}


def clean_text(value: Any) -> str:
    return str(value or "").strip()


def optional_text(value: Any) -> str | None:
    text = clean_text(value)
    return text if text else None


def normalize_chart_title_mode(value: Any) -> str:
    mode = clean_text(value).lower()
    return mode if mode in VALID_TITLE_MODES else "blank"


def ensure_file_extension(path: str | Path, extension: str) -> str:
    """Return path as string with the requested extension.

    extension may be ".xlsx" or "xlsx".
    """
    text = str(path)

    ext = clean_text(extension)
    if not ext:
        return text

    if not ext.startswith("."):
        ext = "." + ext

    if not text.lower().endswith(ext.lower()):
        text += ext

    return text


def sanitize_filename_stem(value: Any, fallback: str = "export") -> str:
    """Return a filesystem-safe filename stem without extension."""
    text = clean_text(value)

    if not text:
        text = fallback

    text = re.sub(r'[<>:"/\\|?*]+', "_", text)
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"_+", "_", text)
    text = text.strip("._ ")

    return text or fallback


def default_single_raman_export_filename(current_path: str | Path | None) -> str:
    if current_path:
        stem = Path(current_path).with_suffix("").name
        return sanitize_filename_stem(stem + "_processed") + ".xlsx"

    return "processed_output.xlsx"


def default_batch_raman_export_filename(batch_folder: str | Path | None) -> str:
    if batch_folder:
        name = Path(batch_folder).name
        return sanitize_filename_stem(name + "_batch_processed") + ".xlsx"

    return "batch_processed.xlsx"


def default_paax_export_filename(study: Any, trace_name: Any, extension: str) -> str:
    stem = sanitize_filename_stem(f"{clean_text(study)}_{clean_text(trace_name)}", fallback="paax_trace")
    return ensure_file_extension(stem, extension)


def safe_excel_sheet_name(name: Any, used: Iterable[str] | None = None, fallback: str = "sheet") -> str:
    """Excel sheet names must be <=31 characters and cannot contain []:*?/\\."""
    used_set = {str(x) for x in (used or [])}

    base = clean_text(name)
    base = re.sub(r"[:\\/?*\[\]]+", "_", base)
    base = base.strip("' ")

    if not base:
        base = fallback

    base = base[:31]

    candidate = base
    counter = 2

    while candidate in used_set:
        suffix = f"_{counter}"
        candidate = base[: 31 - len(suffix)] + suffix
        counter += 1

    return candidate


def batch_export_mode(
    current_plot_mode: Any,
    *,
    data_are_reference_subtracted: bool,
) -> str:
    """Choose the Excel batch plot mode from the current plot state."""
    mode = clean_text(current_plot_mode).lower() or "overlay"

    if mode == "single":
        return "overlay"

    if mode == "reference_subtracted_stacked" and not data_are_reference_subtracted:
        return "stacked"

    if mode in {"overlay", "stacked", "reference_subtracted_stacked"}:
        return mode

    return "overlay"


def reference_subtraction_export_warning_needed(
    current_plot_mode: Any,
    *,
    data_are_reference_subtracted: bool,
) -> bool:
    return (
        clean_text(current_plot_mode).lower() == "reference_subtracted_stacked"
        and not data_are_reference_subtracted
    )


def current_batch_export_labels(
    *,
    traces: list[dict],
    current_plot_mode: Any,
    batch_specs: list[Any],
    batch_labels: list[str],
) -> list[str]:
    """Return labels for batch export, preferring current trace-table labels."""
    mode = clean_text(current_plot_mode).lower()

    if traces and mode in {"overlay", "stacked", "reference_subtracted_stacked"}:
        labels = [
            clean_text(tr.get("label", ""))
            for tr in traces
            if clean_text(tr.get("role", "")).lower() in {"processed", "ref-sub processed"}
        ]

        if len(labels) == len(batch_specs):
            return labels

    if batch_labels:
        return [str(x) for x in batch_labels]

    out: list[str] = []

    for i, spec in enumerate(batch_specs):
        md = getattr(spec, "metadata", {}) or {}

        label = (
            md.get("legend_label")
            or md.get("filename_stem")
            or f"Spectrum_{i + 1}"
        )

        out.append(str(label))

    return out


def per_sheet_titles_from_specs(batch_specs: list[Any]) -> list[str]:
    return [
        str((getattr(spec, "metadata", {}) or {}).get("chart_title") or "")
        for spec in batch_specs
    ]


def overlay_title_for_batch(
    *,
    mode: Any,
    chart_title_mode: Any,
    chart_title_text: Any,
) -> str | None:
    mode_text = clean_text(mode).lower()
    title_mode = normalize_chart_title_mode(chart_title_mode)
    title_text = clean_text(chart_title_text)

    if title_mode == "custom":
        return title_text or None

    if title_mode == "sample":
        if mode_text == "overlay":
            return "Overlay"

        return mode_text.replace("_", " ") or None

    return None


def batch_mode_needs_stack_offset(mode: Any) -> bool:
    return clean_text(mode).lower() in {"stacked", "reference_subtracted_stacked"}