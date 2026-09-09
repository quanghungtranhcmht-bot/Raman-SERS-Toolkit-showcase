from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import math


@dataclass(frozen=True)
class ReferenceInputPlan:
    ok: bool
    compound_name: str = ""
    concentration_M: float | None = None
    notes: str = ""
    error_title: str = ""
    error_message: str = ""


def clean_library_text(value: Any) -> str:
    return str(value or "").strip()


def parse_optional_concentration(value: Any) -> tuple[float | None, str | None]:
    """Parse optional concentration text.

    Returns:
        (concentration, error_message)

    Blank concentration is allowed and becomes None.
    """
    text = clean_library_text(value)

    if not text:
        return None, None

    try:
        concentration = float(text)
    except Exception:
        return None, "Concentration must be numeric, for example 5e-5."

    if not math.isfinite(concentration):
        return None, "Concentration must be a finite numeric value."

    if concentration < 0:
        return None, "Concentration cannot be negative."

    return concentration, None


def build_reference_input_plan(
    *,
    processed_spec: Any,
    compound_text: Any,
    concentration_text: Any,
    notes_text: Any,
) -> ReferenceInputPlan:
    """Validate Library-tab fields before saving a reference spectrum."""
    if processed_spec is None:
        return ReferenceInputPlan(
            ok=False,
            error_title="No processed spectrum",
            error_message="Run Processing on a reference spectrum first.",
        )

    compound = clean_library_text(compound_text)

    if not compound:
        return ReferenceInputPlan(
            ok=False,
            error_title="Missing compound name",
            error_message="Enter the reference compound name first.",
        )

    concentration, err = parse_optional_concentration(concentration_text)

    if err:
        return ReferenceInputPlan(
            ok=False,
            compound_name=compound,
            error_title="Invalid concentration",
            error_message=err,
        )

    return ReferenceInputPlan(
        ok=True,
        compound_name=compound,
        concentration_M=concentration,
        notes=clean_library_text(notes_text),
    )


def add_reference_kwargs(plan: ReferenceInputPlan) -> dict[str, Any]:
    """Build kwargs for spectral_library.add_reference_spectrum(...)."""
    return {
        "compound_name": plan.compound_name,
        "concentration_M": plan.concentration_M,
        "notes": plan.notes,
    }


def add_reference_log_notes(plan: ReferenceInputPlan) -> str:
    parts = [f"compound={plan.compound_name}"]

    if plan.concentration_M is not None:
        parts.append(f"concentration_M={plan.concentration_M:g}")

    return "; ".join(parts)


def added_reference_status(row: dict, compound_name: str) -> str:
    ref_id = row.get("reference_id", "")
    return f"Added library reference: {compound_name} ({ref_id})"


def added_reference_message(compound_name: str) -> str:
    return f"Added {compound_name} to the SERS library."


def can_search_library(processed_spec: Any) -> tuple[bool, str, str]:
    if processed_spec is None:
        return (
            False,
            "No processed spectrum",
            "Run Processing on an unknown spectrum first.",
        )

    return True, "", ""


def format_score(value: Any, digits: int = 4) -> str:
    try:
        score = float(value)
    except Exception:
        return ""

    if not math.isfinite(score):
        return ""

    return f"{score:.{digits}f}"


def search_result_table_values(result: dict, rank: int) -> list[str]:
    """Return values for the current 4-column Library result table."""
    return [
        str(rank),
        clean_library_text(result.get("compound_name", "")),
        format_score(result.get("score", 0.0), digits=4),
        clean_library_text(result.get("reference_id", "")),
    ]


def search_result_table_rows(results: list[dict]) -> list[list[str]]:
    return [
        search_result_table_values(result, row_idx + 1)
        for row_idx, result in enumerate(results)
    ]


def search_status_message(results: list[dict]) -> str:
    """Scientific wording: search is a candidate match, not proof."""
    if not results:
        return "No library matches found."

    top = results[0]

    compound = clean_library_text(top.get("compound_name", ""))
    score = format_score(top.get("score", 0.0), digits=3)

    if compound and score:
        return f"Top candidate library match: {compound} (score {score})"

    if compound:
        return f"Top candidate library match: {compound}"

    return "Top candidate library match found."


def best_match_summary(results: list[dict]) -> str:
    """Short text suitable for future result panels/reports."""
    if not results:
        return "No candidate reference match found."

    top = results[0]
    compound = clean_library_text(top.get("compound_name", "Unknown reference"))
    ref_id = clean_library_text(top.get("reference_id", ""))
    score = format_score(top.get("score", 0.0), digits=3)
    cosine = format_score(top.get("cosine", ""), digits=3)
    pearson = format_score(top.get("pearson", ""), digits=3)

    details: list[str] = []

    if score:
        details.append(f"score {score}")

    if cosine:
        details.append(f"cosine {cosine}")

    if pearson:
        details.append(f"Pearson {pearson}")

    if ref_id:
        details.append(f"reference {ref_id}")

    suffix = f" ({'; '.join(details)})" if details else ""

    return f"Best candidate reference match: {compound}{suffix}. This is not definitive identification."


def reference_display_label(row: dict) -> str:
    compound = clean_library_text(row.get("compound_name", "Unknown compound"))
    ref_id = clean_library_text(row.get("reference_id", ""))

    concentration = row.get("concentration_M", None)
    concentration_text = ""

    if concentration not in (None, ""):
        try:
            concentration_text = f", {float(concentration):g} M"
        except Exception:
            concentration_text = f", {concentration} M"

    if ref_id:
        return f"{compound}{concentration_text} [{ref_id}]"

    return f"{compound}{concentration_text}"