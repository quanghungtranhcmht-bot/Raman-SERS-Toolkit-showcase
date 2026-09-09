from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import math

from ecsers_analyzer.domain.recipe import ProcessingRecipe


ALLOWED_BASELINES = {"none", "airpls", "als", "poly"}
ALLOWED_NORMALIZATIONS = {"none", "max", "area", "vector", "power_time", "power*time"}


@dataclass(frozen=True)
class ProcessingFormValues:
    despike_checked: bool
    despike_window: Any
    despike_threshold: Any
    despike_max_width_points: Any

    baseline: Any
    lam: Any
    max_iter: Any

    smooth_checked: bool
    smooth_window_points: Any
    smooth_width_enabled: bool
    smooth_width_cm1: Any
    smooth_polyorder: Any

    normalize: Any
    laser_power_mw: Any


@dataclass(frozen=True)
class ProcessingRecipePlan:
    ok: bool
    recipe: ProcessingRecipe | None = None

    needs_acquisition_time: bool = False
    acquisition_time_default_s: float = 20.0

    error_title: str = ""
    error_message: str = ""


def clean_processing_text(value: Any) -> str:
    return str(value or "").strip()


def normalize_choice(value: Any) -> str:
    return clean_processing_text(value).lower()


def parse_float_field(
    value: Any,
    *,
    field_name: str,
    default: float | None = None,
    allow_blank: bool = True,
    min_value: float | None = None,
    must_be_greater_than_min: bool = False,
) -> tuple[float | None, str | None]:
    text = clean_processing_text(value)

    if not text:
        if allow_blank:
            return default, None
        return None, f"{field_name} is required."

    try:
        number = float(text)
    except Exception:
        return None, f"{field_name} must be numeric."

    if not math.isfinite(number):
        return None, f"{field_name} must be a finite number."

    if min_value is not None:
        if must_be_greater_than_min:
            if number <= min_value:
                return None, f"{field_name} must be greater than {min_value}."
        else:
            if number < min_value:
                return None, f"{field_name} must be at least {min_value}."

    return number, None


def parse_int_field(
    value: Any,
    *,
    field_name: str,
    default: int | None = None,
    allow_blank: bool = True,
    min_value: int | None = None,
) -> tuple[int | None, str | None]:
    text = clean_processing_text(value)

    if not text:
        if allow_blank:
            return default, None
        return None, f"{field_name} is required."

    try:
        number = int(float(text))
    except Exception:
        return None, f"{field_name} must be an integer."

    if min_value is not None and number < min_value:
        return None, f"{field_name} must be at least {min_value}."

    return number, None


def integration_time_from_raw_spec(raw_spec: Any) -> float | None:
    md = dict(getattr(raw_spec, "metadata", {}) or {}) if raw_spec is not None else {}

    value = md.get("integration_time_s", None)

    try:
        t = float(value)
    except Exception:
        return None

    if not math.isfinite(t) or t <= 0:
        return None

    return t


def build_baseline_params(
    *,
    baseline: str,
    lam_text: Any,
    max_iter_text: Any,
) -> tuple[dict[str, Any], str | None]:
    """Build baseline_params while preserving current behavior.

    Current UI behavior only uses lam/max_iter for airPLS.
    ALS/poly use their internal defaults.
    """
    if baseline != "airpls":
        return {}, None

    lam, err = parse_float_field(
        lam_text,
        field_name="airPLS lambda",
        default=1e5,
        min_value=0.0,
        must_be_greater_than_min=True,
    )
    if err:
        return {}, err

    max_iter, err = parse_int_field(
        max_iter_text,
        field_name="baseline max iterations",
        default=80,
        min_value=1,
    )
    if err:
        return {}, err

    return {
        "lam": lam,
        "max_iter": max_iter,
        "tol": 1e-3,
        "w_min": 1e-6,
        "exp_clip": 15.0,
    }, None


def build_processing_recipe_from_form(
    form: ProcessingFormValues,
    *,
    raw_spec: Any = None,
    provided_integration_time_s: float | None = None,
) -> ProcessingRecipePlan:
    baseline = normalize_choice(form.baseline) or "none"

    if baseline not in ALLOWED_BASELINES:
        return ProcessingRecipePlan(
            ok=False,
            error_title="Invalid baseline",
            error_message=f"Unknown baseline method: {baseline}",
        )

    baseline_params, err = build_baseline_params(
        baseline=baseline,
        lam_text=form.lam,
        max_iter_text=form.max_iter,
    )

    if err:
        return ProcessingRecipePlan(
            ok=False,
            error_title="Invalid baseline setting",
            error_message=err,
        )

    if bool(form.smooth_checked):
        smooth_window_points, err = parse_int_field(
            form.smooth_window_points,
            field_name="SavGol smoothing window",
            default=5,
            min_value=0,
        )
        if err:
            return ProcessingRecipePlan(
                ok=False,
                error_title="Invalid smoothing setting",
                error_message=err,
            )

        smooth_polyorder, err = parse_int_field(
            form.smooth_polyorder,
            field_name="SavGol polyorder",
            default=2,
            min_value=1,
        )
        if err:
            return ProcessingRecipePlan(
                ok=False,
                error_title="Invalid smoothing setting",
                error_message=err,
            )

        smooth_width_cm1 = None

        if bool(form.smooth_width_enabled):
            smooth_width_cm1, err = parse_float_field(
                form.smooth_width_cm1,
                field_name="SavGol width in cm⁻¹",
                default=8.0,
                min_value=0.0,
                must_be_greater_than_min=True,
            )
            if err:
                return ProcessingRecipePlan(
                    ok=False,
                    error_title="Invalid smoothing setting",
                    error_message=err,
                )
    else:
        # Explicit OFF state. Stale text in disabled controls cannot alter data.
        smooth_window_points = 0
        smooth_width_cm1 = None
        smooth_polyorder = 2

    if bool(form.despike_checked):
        despike_window, err = parse_int_field(
            form.despike_window,
            field_name="despike window",
            default=7,
            min_value=3,
        )
        if err:
            return ProcessingRecipePlan(
                ok=False,
                error_title="Invalid despike setting",
                error_message=err,
            )

        despike_threshold, err = parse_float_field(
            form.despike_threshold,
            field_name="despike threshold",
            default=7.0,
            min_value=0.0,
            must_be_greater_than_min=True,
        )
        if err:
            return ProcessingRecipePlan(
                ok=False,
                error_title="Invalid despike setting",
                error_message=err,
            )

        despike_max_width_points, err = parse_int_field(
            form.despike_max_width_points,
            field_name="maximum cosmic-ray width",
            default=1,
            min_value=1,
        )
        if err:
            return ProcessingRecipePlan(
                ok=False,
                error_title="Invalid despike setting",
                error_message=err,
            )
    else:
        despike_window = 7
        despike_threshold = 7.0
        despike_max_width_points = 1

    normalize = normalize_choice(form.normalize) or "none"

    if normalize not in ALLOWED_NORMALIZATIONS:
        return ProcessingRecipePlan(
            ok=False,
            error_title="Invalid normalization",
            error_message=f"Unknown normalization method: {normalize}",
        )

    if normalize == "power*time":
        normalize = "power_time"

    normalize_recipe = None if normalize == "none" else normalize

    laser_power_mw, err = parse_float_field(
        form.laser_power_mw,
        field_name="laser power",
        default=None,
        allow_blank=True,
        min_value=0.0,
        must_be_greater_than_min=True,
    )
    if err:
        return ProcessingRecipePlan(
            ok=False,
            error_title="Invalid laser power",
            error_message=err,
        )

    integration_time_s = None

    if normalize_recipe == "power_time":
        if laser_power_mw is None:
            return ProcessingRecipePlan(
                ok=False,
                error_title="Laser power required",
                error_message="power_time normalization requires a positive laser power in mW.",
            )

        if provided_integration_time_s is not None:
            try:
                integration_time_s = float(provided_integration_time_s)
            except Exception:
                integration_time_s = None

            if integration_time_s is None or not math.isfinite(integration_time_s) or integration_time_s <= 0:
                return ProcessingRecipePlan(
                    ok=False,
                    error_title="Invalid acquisition time",
                    error_message="Acquisition time must be a positive number of seconds.",
                )
        else:
            integration_time_s = integration_time_from_raw_spec(raw_spec)

        if integration_time_s is None:
            return ProcessingRecipePlan(
                ok=False,
                needs_acquisition_time=True,
                acquisition_time_default_s=20.0,
                error_title="Acquisition time required",
                error_message="power_time normalization requires acquisition time in seconds.",
            )

    recipe = ProcessingRecipe(
        despike=bool(form.despike_checked),
        despike_window=int(despike_window),
        despike_threshold=float(despike_threshold),
        despike_max_width_points=int(despike_max_width_points),
        baseline=None if baseline == "none" else baseline,
        baseline_params=baseline_params,
        smooth_window_points=int(smooth_window_points),
        smooth_width_cm1=smooth_width_cm1,
        smooth_polyorder=int(smooth_polyorder),
        normalize=normalize_recipe,
        laser_power_mw=laser_power_mw,
        integration_time_s=integration_time_s,
    )

    return ProcessingRecipePlan(ok=True, recipe=recipe)