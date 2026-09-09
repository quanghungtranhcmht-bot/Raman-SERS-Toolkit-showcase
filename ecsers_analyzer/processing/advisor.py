from __future__ import annotations

from dataclasses import dataclass, field

from ecsers_analyzer.domain.recipe import ProcessingRecipe
from ecsers_analyzer.processing.analysis_features import extract_spectrum_features


@dataclass
class ProcessingRecommendation:
    recipe: ProcessingRecipe
    reasons: list[str] = field(default_factory=list)
    features: dict = field(default_factory=dict)


def recommend_recipe(raw_spec, *, purpose: str = "plot") -> ProcessingRecommendation:
    """
    Recommend a ProcessingRecipe for a raw Raman/SERS spectrum.

    purpose:
      - "plot": cleaner visual comparison
      - "quantitative": preserve intensity scaling more carefully
    """
    features = extract_spectrum_features(raw_spec)

    reasons = []

    noise_rel = features.get("noise_relative")
    curvature = features.get("baseline_curvature") or 0.0
    spike_count = features.get("estimated_spike_count") or 0

    md = dict(getattr(raw_spec, "metadata", {}) or {})

    # ---------------- baseline recommendation ----------------
    if curvature >= 0.25:
        baseline_lam = 1e6
        reasons.append("Strong broad baseline curvature detected; using stronger airPLS smoothing.")
    else:
        baseline_lam = 1e5
        reasons.append("Moderate/normal baseline curvature; using standard airPLS settings.")

    baseline_params = {
        "lam": baseline_lam,
        "max_iter": 100,
        "tol": 1e-3,
        "w_min": 1e-6,
        "exp_clip": 15.0,
    }

    # ---------------- despike recommendation ----------------
    # Use the same conservative isolated-positive-event detector as processing.
    despike_threshold = 7.0
    despike_max_width_points = 1
    despike = spike_count > 0

    candidate_count = features.get("estimated_spike_candidate_count") or 0
    if despike:
        reasons.append(
            f"{spike_count} isolated positive cosmic-ray candidate(s) detected; "
            "conservative single-point despiking is recommended."
        )
    elif candidate_count > 0:
        reasons.append(
            f"{candidate_count} locally extreme point(s) belong to multi-point features; "
            "despiking is left off to protect narrow Raman/SERS bands."
        )
    else:
        reasons.append("No convincing isolated cosmic-ray events detected; despiking is left off.")

    # ---------------- smoothing recommendation ----------------
    # Keep smoothing off when noise is low/unknown or for quantitative work.
    # When needed, recommend only a small 5- or 7-point equivalent window.
    dx = features.get("x_spacing_cm1")
    smooth_polyorder = 2
    smooth_points = 0
    smooth_width = None

    if purpose == "quantitative":
        reasons.append("Quantitative purpose selected; smoothing is left off to preserve peak height.")
    elif noise_rel is None:
        reasons.append("Noise level could not be estimated reliably; smoothing is left off.")
    elif noise_rel >= 0.08:
        smooth_points = 7
        if dx is not None:
            smooth_width = float(dx) * smooth_points
        reasons.append("High relative noise detected; recommending mild 7-point SavGol smoothing.")
    elif noise_rel >= 0.04:
        smooth_points = 5
        if dx is not None:
            smooth_width = float(dx) * smooth_points
        reasons.append("Moderate noise detected; recommending mild 5-point SavGol smoothing.")
    else:
        reasons.append("Low relative noise detected; smoothing is left off to preserve narrow peaks.")

    # ---------------- normalization recommendation ----------------
    if purpose == "quantitative":
        normalize = None
        reasons.append("Quantitative purpose selected; leaving normalization as none by default.")
    else:
        normalize = "max"
        reasons.append("Plot purpose selected; recommending max normalization for visual comparison.")

    recipe = ProcessingRecipe(
        despike=despike,
        despike_window=7,
        despike_threshold=despike_threshold,
        despike_max_width_points=despike_max_width_points,
        baseline="airpls",
        baseline_params=baseline_params,
        smooth_window_points=smooth_points,
        smooth_width_cm1=smooth_width,
        smooth_polyorder=smooth_polyorder,
        normalize=normalize,
        laser_power_mw=md.get("laser_power_mw", 34.1),
        integration_time_s=md.get("integration_time_s", None),
    )

    return ProcessingRecommendation(
        recipe=recipe,
        reasons=reasons,
        features=features,
    )