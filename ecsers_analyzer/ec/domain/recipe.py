from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional, Any


@dataclass
class ProcessingRecipe:
    """Reproducible description of one Raman/SERS preprocessing run."""

    # Spike removal. Disabled by default because despiking changes raw intensities.
    # max_width_points protects multi-point Raman bands from being treated as
    # single-pixel cosmic-ray events.
    despike: bool = False
    despike_window: int = 7
    despike_threshold: float = 7.0
    despike_max_width_points: int = 1

    # Baseline
    baseline: Optional[str] = "airpls"
    baseline_params: dict[str, Any] = field(default_factory=dict)

    # Smoothing. A zero point window plus None cm^-1 width means OFF.
    smooth_window_points: int = 0
    smooth_width_cm1: Optional[float] = None
    smooth_polyorder: int = 2

    # Normalization
    normalize: Optional[str] = None
    laser_power_mw: Optional[float] = 34.1
    integration_time_s: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProcessingRecipe":
        return cls(**dict(data))