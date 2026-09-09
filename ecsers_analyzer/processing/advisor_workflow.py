from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import math

from ecsers_analyzer.domain.recipe import ProcessingRecipe


@dataclass(frozen=True)
class AdvisorRunPlan:
    ok: bool
    error_title: str = ""
    error_message: str = ""


def clean_advisor_text(value: Any) -> str:
    return str(value or "").strip()


def can_run_advisor(raw_spec: Any) -> AdvisorRunPlan:
    if raw_spec is None:
        return AdvisorRunPlan(
            ok=False,
            error_title="No spectrum",
            error_message="Open a spectrum or select a batch folder first.",
        )

    return AdvisorRunPlan(ok=True)


def format_advisor_value(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        return f"{value:.6g}"

    return str(value)


def recipe_ui_values(recipe: ProcessingRecipe) -> dict[str, Any]:
    """Convert a ProcessingRecipe into UI-control values.

    This does not touch Qt widgets directly. The UI applies these values.
    """
    params = dict(recipe.baseline_params or {})

    return {
        "despike_checked": bool(recipe.despike),
        "despike_window": str(recipe.despike_window),
        "despike_threshold": str(recipe.despike_threshold),
        "despike_max_width_points": str(recipe.despike_max_width_points),
        "baseline": str(recipe.baseline or "none"),
        "lam": format_advisor_value(params.get("lam")),
        "max_iter": format_advisor_value(params.get("max_iter")),
        "smooth_checked": bool(recipe.smooth_width_cm1 is not None or int(recipe.smooth_window_points or 0) > 0),
        "smooth_window_points": str(recipe.smooth_window_points),
        "smooth_width_enabled": recipe.smooth_width_cm1 is not None,
        "smooth_width_cm1": format_advisor_value(recipe.smooth_width_cm1),
        "smooth_polyorder": str(recipe.smooth_polyorder),
        "normalize": str(recipe.normalize or "none"),
        "laser_power_mw": format_advisor_value(recipe.laser_power_mw),
    }


def recipe_summary_lines(recipe: ProcessingRecipe) -> list[str]:
    params = dict(recipe.baseline_params or {})

    lines = [
        f"Baseline: {recipe.baseline or 'none'}",
        f"airPLS λ: {format_advisor_value(params.get('lam'))}",
        f"Baseline max iterations: {format_advisor_value(params.get('max_iter'))}",
        (
            f"Despike: {bool(recipe.despike)}, threshold {recipe.despike_threshold}, "
            f"max width {recipe.despike_max_width_points} point(s)"
        ),
    ]

    smoothing_on = recipe.smooth_width_cm1 is not None or int(recipe.smooth_window_points or 0) > 0
    if smoothing_on:
        lines.extend([
            f"SavGol width: {format_advisor_value(recipe.smooth_width_cm1)} cm⁻¹",
            f"SavGol points: {recipe.smooth_window_points}",
            f"SavGol polyorder: {recipe.smooth_polyorder}",
        ])
    else:
        lines.append("SavGol smoothing: off")

    lines.append(f"Normalize: {recipe.normalize or 'none'}")
    return lines


def reason_lines(reasons: list[str] | tuple[str, ...] | None) -> list[str]:
    out: list[str] = []

    for reason in reasons or []:
        text = clean_advisor_text(reason)
        if text:
            out.append(f"- {text}")

    return out or ["- No explanation was provided."]


def format_feature_value(value: Any) -> str:
    if value is None:
        return ""

    try:
        number = float(value)
    except Exception:
        return str(value)

    if not math.isfinite(number):
        return ""

    return f"{number:.6g}"


def feature_summary_lines(features: dict[str, Any] | None) -> list[str]:
    if not features:
        return []

    lines: list[str] = []

    for key, value in features.items():
        formatted = format_feature_value(value)
        if formatted != "":
            lines.append(f"{key}: {formatted}")

    return lines


def recommendation_dialog_message(recommendation: Any) -> str:
    """Build the transparent advisor explanation shown to the user."""
    recipe = recommendation.recipe

    recipe_text = "\n".join(recipe_summary_lines(recipe))
    reasons_text = "\n".join(reason_lines(getattr(recommendation, "reasons", [])))

    feature_lines = feature_summary_lines(getattr(recommendation, "features", {}) or {})
    feature_block = ""

    if feature_lines:
        feature_block = "\n\nMeasured features:\n" + "\n".join(feature_lines)

    return (
        "Recommended processing settings:\n\n"
        f"{recipe_text}\n\n"
        "Reasons:\n"
        f"{reasons_text}"
        f"{feature_block}\n\n"
        "Apply these settings to the Processing tab?"
    )


def advisor_status_applied() -> str:
    return (
        "Recommended processing settings applied. "
        "Click Run Processing or Run Batch Processing + Plot."
    )


def advisor_status_rejected() -> str:
    return "Recommendation viewed but not applied."


def advisor_log_notes(recommendation: Any, *, decision: str) -> str:
    """Short reproducible note for local user-history logging."""
    recipe = recommendation.recipe
    params = dict(recipe.baseline_params or {})

    reasons = "; ".join(clean_advisor_text(r) for r in getattr(recommendation, "reasons", []) if clean_advisor_text(r))

    parts = [
        f"decision={clean_advisor_text(decision)}",
        f"baseline={recipe.baseline or 'none'}",
        f"lam={format_advisor_value(params.get('lam'))}",
        f"despike={bool(recipe.despike)}",
        f"despike_threshold={recipe.despike_threshold}",
        f"despike_max_width_points={recipe.despike_max_width_points}",
        f"smooth_width_cm1={format_advisor_value(recipe.smooth_width_cm1)}",
        f"smooth_window_points={recipe.smooth_window_points}",
        f"smooth_polyorder={recipe.smooth_polyorder}",
        f"normalize={recipe.normalize or 'none'}",
    ]

    if reasons:
        parts.append(f"reasons={reasons}")

    return "; ".join(parts)