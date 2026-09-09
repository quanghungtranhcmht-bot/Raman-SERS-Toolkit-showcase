from __future__ import annotations

from ecsers_analyzer.domain.spectrum import Spectrum
from ecsers_analyzer.domain.recipe import ProcessingRecipe

def process_spectrum(raw_spec, recipe: ProcessingRecipe, label: str = "") -> Spectrum:
    """
    Apply one ProcessingRecipe to one raw Spectrum.

    This function is shared by single mode and batch mode, so both paths use
    the exact same preprocessing logic.
    """
    md = dict(getattr(raw_spec, "metadata", {}) or {})

    if recipe.laser_power_mw is not None:
        md["laser_power_mw"] = float(recipe.laser_power_mw)

    if recipe.integration_time_s is not None:
        md["integration_time_s"] = float(recipe.integration_time_s)

    if label:
        md["legend_label"] = label

    baseline = recipe.baseline
    if baseline is not None and str(baseline).lower() == "none":
        baseline = None

    normalize = recipe.normalize
    if normalize is not None and str(normalize).lower() == "none":
        normalize = None

    spec = Spectrum(
        raw_spec.x_raw.copy(),
        raw_spec.y_raw.copy(),
        metadata=md,
    )

    spec.preprocess(
        baseline=baseline,
        baseline_params=dict(recipe.baseline_params or {}),
        smooth_window=recipe.smooth_window_points,
        smooth_width_cm1=recipe.smooth_width_cm1,
        smooth_polyorder=recipe.smooth_polyorder,
        normalize=normalize,
        despike=bool(recipe.despike),
        despike_params={
            "window": int(recipe.despike_window),
            "threshold": float(recipe.despike_threshold),
            "max_width_points": int(recipe.despike_max_width_points),
        },
    )

    # Make the recipe directly accessible from the processed Spectrum.
    spec.processing_recipe_object = recipe

    return spec