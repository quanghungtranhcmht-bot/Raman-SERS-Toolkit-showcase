from __future__ import annotations

from dataclasses import dataclass


VALID_ROI_ROLES = [
    "peak",
    "noise",
    "normalization",
    "baseline_exclude",
    "integration",
]


@dataclass(frozen=True)
class RoiLimits:
    xmin: float
    xmax: float

    @property
    def width(self) -> float:
        return abs(self.xmax - self.xmin)


def normalize_roi_limits(xmin: float, xmax: float) -> RoiLimits:
    """Return ordered ROI limits or raise ValueError."""
    lo = min(float(xmin), float(xmax))
    hi = max(float(xmin), float(xmax))

    if hi <= lo:
        raise ValueError("ROI maximum must be greater than ROI minimum.")

    return RoiLimits(xmin=lo, xmax=hi)


def parse_roi_limits(xmin_text: str, xmax_text: str) -> RoiLimits:
    """Parse ROI limits from UI text."""
    try:
        xmin = float(xmin_text)
        xmax = float(xmax_text)
    except Exception as exc:
        raise ValueError("ROI limits must be numeric.") from exc

    return normalize_roi_limits(xmin, xmax)


def roi_default_label(role: str, xmin: float, xmax: float) -> str:
    role = clean_roi_role(role)
    limits = normalize_roi_limits(xmin, xmax)
    return f"{role}: {limits.xmin:.0f}–{limits.xmax:.0f} cm⁻¹"


def clean_roi_role(role: str) -> str:
    role = str(role or "peak").strip().lower()
    if role not in VALID_ROI_ROLES:
        return "peak"
    return role


def should_auto_update_roi_label(label: str, role: str) -> bool:
    label = str(label or "")
    role = clean_roi_role(role)
    return not label or label.startswith(role + ":") or ":" in label