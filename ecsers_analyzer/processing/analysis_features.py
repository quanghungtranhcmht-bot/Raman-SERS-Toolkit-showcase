from __future__ import annotations

import numpy as np
from ecsers_analyzer.processing.preprocessing import detect_cosmic_ray_masks


def robust_mad(values) -> float:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]

    if values.size == 0:
        return float("nan")

    med = np.nanmedian(values)
    return float(1.4826 * np.nanmedian(np.abs(values - med)))


def _finite_xy(spec, raw: bool = True):
    if raw and hasattr(spec, "x_raw") and hasattr(spec, "y_raw"):
        x = np.asarray(spec.x_raw, dtype=float)
        y = np.asarray(spec.y_raw, dtype=float)
    else:
        x = np.asarray(spec.x, dtype=float)
        y = np.asarray(spec.y, dtype=float)

    finite = np.isfinite(x) & np.isfinite(y)
    return x[finite], y[finite]


def _window_mask(x, window):
    lo, hi = float(min(window)), float(max(window))
    return (x >= lo) & (x <= hi)


def estimate_spike_diagnostics(
    y,
    window: int = 7,
    threshold: float = 7.0,
    max_width_points: int = 1,
) -> tuple[int, int]:
    """Return ``(candidate_count, accepted_cosmic_ray_count)``."""
    y = np.asarray(y, dtype=float)
    y = y[np.isfinite(y)]

    if y.size == 0:
        return 0, 0

    candidates, accepted = detect_cosmic_ray_masks(
        y,
        window=window,
        threshold=threshold,
        max_width_points=max_width_points,
    )
    return int(np.sum(candidates)), int(np.sum(accepted))


def estimate_spike_count(
    y,
    window: int = 7,
    threshold: float = 7.0,
    max_width_points: int = 1,
) -> int:
    """Estimate conservative isolated cosmic-ray events."""
    _, accepted = estimate_spike_diagnostics(
        y,
        window=window,
        threshold=threshold,
        max_width_points=max_width_points,
    )
    return accepted


def estimate_baseline_curvature(x, y) -> float:
    """
    Rough fluorescence/background curvature score.
    Larger value means stronger broad baseline shape.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    finite = np.isfinite(x) & np.isfinite(y)
    x = x[finite]
    y = y[finite]

    if x.size < 20:
        return 0.0

    x_scaled = (x - np.nanmean(x)) / (np.nanstd(x) or 1.0)

    try:
        p1 = np.polyfit(x_scaled, y, 1)
        p2 = np.polyfit(x_scaled, y, 2)

        y1 = np.polyval(p1, x_scaled)
        y2 = np.polyval(p2, x_scaled)

        curvature_amp = np.nanmax(np.abs(y2 - y1))
        signal_amp = np.nanmax(y) - np.nanmin(y)

        if signal_amp <= 0 or not np.isfinite(signal_amp):
            return 0.0

        return float(curvature_amp / signal_amp)

    except Exception:
        return 0.0


def extract_spectrum_features(
    spec,
    *,
    analysis_window=(400, 1700),
    noise_window=(1800, 2000),
) -> dict:
    """
    Extract simple features used by the processing advisor.
    """
    x, y = _finite_xy(spec, raw=True)

    if x.size == 0:
        return {
            "n_points": 0,
            "x_min": None,
            "x_max": None,
            "x_spacing_cm1": None,
            "noise_mad": None,
            "noise_relative": None,
            "signal_range": None,
            "baseline_curvature": None,
            "estimated_spike_candidate_count": 0,
            "estimated_spike_count": 0,
        }

    m_analysis = _window_mask(x, analysis_window)
    xa = x[m_analysis] if np.any(m_analysis) else x
    ya = y[m_analysis] if np.any(m_analysis) else y

    # Prefer noise window. If missing, use top 15% of x-range as fallback.
    m_noise = _window_mask(x, noise_window)

    if not np.any(m_noise):
        cutoff = np.nanpercentile(x, 85)
        m_noise = x >= cutoff

    yn = y[m_noise] if np.any(m_noise) else y

    dx = np.nanmedian(np.abs(np.diff(np.sort(x)))) if x.size > 2 else float("nan")
    signal_range = float(np.nanmax(ya) - np.nanmin(ya)) if ya.size else float("nan")
    noise_mad = robust_mad(yn)

    if np.isfinite(signal_range) and signal_range > 0 and np.isfinite(noise_mad):
        noise_relative = float(noise_mad / signal_range)
    else:
        noise_relative = float("nan")

    spike_candidate_count, spike_count = estimate_spike_diagnostics(ya)

    return {
        "n_points": int(x.size),
        "x_min": float(np.nanmin(x)),
        "x_max": float(np.nanmax(x)),
        "x_spacing_cm1": float(dx) if np.isfinite(dx) else None,
        "noise_mad": float(noise_mad) if np.isfinite(noise_mad) else None,
        "noise_relative": float(noise_relative) if np.isfinite(noise_relative) else None,
        "signal_range": signal_range if np.isfinite(signal_range) else None,
        "baseline_curvature": estimate_baseline_curvature(xa, ya),
        "estimated_spike_candidate_count": spike_candidate_count,
        "estimated_spike_count": spike_count,
    }