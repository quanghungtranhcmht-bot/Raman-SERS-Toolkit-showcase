from __future__ import annotations
import numpy as np
import json
from ecsers_analyzer.processing.preprocessing import Preprocessor, window_points_from_cm1

def _excel_x_axis_label() -> str:
    """Excel-safe x-axis label."""
    return "Raman Shift (cm⁻¹)"


def _excel_y_axis_label_for_spec(spec) -> str:
    """Dynamic Excel y-axis label based on normalization."""
    norm = str(getattr(spec, "normalization_method", "") or "").lower()

    if norm in ("power_time", "power*time"):
        return "Intensity (ADU mW⁻¹ s⁻¹)"

    if norm in ("max", "area", "vector", "l2"):
        return "Normalized Intensity (a.u.)"

    return "Intensity (a.u.)"


def _excel_y_axis_label_for_overlay(spectra) -> str:
    """Use one y-axis label for overlay. If mixed normalization, use generic label."""
    labels = {
        _excel_y_axis_label_for_spec(s)
        for s in spectra
    }

    if len(labels) == 1:
        return labels.pop()

    return "Processed Intensity (a.u.)"


def _excel_x_limits(x, xlim):
    """Return exact Excel x-axis limits.

    Uses GUI/export xlim directly when provided, so 400–1700 stays exact.
    """
    x = np.asarray(x, dtype=float)

    if xlim:
        return float(min(xlim)), float(max(xlim))

    return float(np.nanmin(x)), float(np.nanmax(x))


def _excel_roi_mask(x, xlim):
    """Mask for y-axis scaling inside the requested x-range."""
    x = np.asarray(x, dtype=float)

    if not xlim:
        return np.ones_like(x, dtype=bool)

    lo, hi = float(min(xlim)), float(max(xlim))
    return (x >= lo) & (x <= hi)


def _xlsxwriter_x_axis_options(x, xlim, fontsize):
    x_min, x_max = _excel_x_limits(x, xlim)

    return {
        "name": _excel_x_axis_label(),
        "min": x_min,
        "max": x_max,
        "num_format": "0",
        "major_tick_mark": "outside",
        "minor_tick_mark": "none",
        "major_gridlines": {"visible": False},
        "name_font": {"size": fontsize},
        "num_font": {"size": fontsize},
    }


def _xlsxwriter_y_axis_options(y_axis_label, y_min=None, y_max=None, y_lock=True, fontsize=12):
    opts = {
        "name": y_axis_label,
        "label_position": "none",
        "major_tick_mark": "outside",
        "minor_tick_mark": "none",
        "major_gridlines": {"visible": False},
        "name_font": {"size": fontsize},
        "num_font": {"size": fontsize},
    }

    if y_lock and y_max is not None:
        opts["max"] = float(y_max)
        opts["min"] = float(y_min) if y_min is not None else 0.0

    return opts
class Spectrum:
    def __init__(self, x, y, metadata=None):
        self.x = np.asarray(x, dtype=float)
        self.y = np.asarray(y, dtype=float)
        self.metadata = metadata or {}

        self.x_raw = self.x.copy()
        self.y_raw = self.y.copy()

        # Diagnostics
        self.baseline = None
        self.y_bc = None  # baseline-corrected, pre-smooth/pre-norm
        self.spike_candidate_mask = None
        self.spike_mask = None
        self.n_spike_candidates = 0
        self.n_spikes_removed = 0

        self.normalization_method = None

    def preprocess(
        self,
        baseline="airpls",
        smooth_window=0,
        normalize=None,
        baseline_params=None,
        *,
        despike=False,
        despike_params=None,
        smooth_polyorder=2,
        smooth_width_cm1=None,
    ):
        baseline_params = baseline_params or {}
        despike_params = despike_params or {}

        prep = Preprocessor(self.x_raw, self.y_raw)

        recipe = {
            "despike": bool(despike),
            "despike_params": dict(despike_params),
            "baseline": baseline,
            "baseline_params": dict(baseline_params),
            "smooth_window_points": smooth_window,
            "smooth_width_cm1": smooth_width_cm1,
            "smooth_polyorder": smooth_polyorder,
            "normalize": normalize,
        }

        # 1. Despike before baseline correction.
        if despike:
            prep.despike_median(**despike_params)

        self.spike_candidate_mask = getattr(prep, "spike_candidate_mask_", None)
        self.spike_mask = getattr(prep, "spike_mask_", None)
        self.n_spike_candidates = int(getattr(prep, "n_spike_candidates_", 0))
        self.n_spikes_removed = int(getattr(prep, "n_spikes_", 0))

        # 2. Baseline correction.
        if baseline:
            b = str(baseline).lower()

            if b == "airpls":
                prep.baseline_airpls(**baseline_params)
            elif b == "als":
                prep.baseline_als(**baseline_params)
            elif b == "poly":
                prep.baseline_poly(**baseline_params)
            else:
                raise ValueError(f"Unknown baseline method: {baseline}")

        self.baseline = getattr(prep, "baseline_", None)
        self.y_bc = prep.y.copy()

        # 3. Smoothing.
        final_smooth_window = smooth_window

        if smooth_width_cm1 is not None:
            try:
                width = float(smooth_width_cm1)
                if width > 0:
                    # Use the smallest legal/practical SavGol window rather than
                    # forcing an 11-point floor that can flatten narrow bands.
                    min_window = max(5, int(smooth_polyorder) + 2)
                    if min_window % 2 == 0:
                        min_window += 1

                    final_smooth_window = window_points_from_cm1(
                        prep.x,
                        width,
                        minimum=min_window,
                    )
                else:
                    final_smooth_window = 0
            except Exception:
                final_smooth_window = smooth_window

        recipe["final_smooth_window_points"] = final_smooth_window

        if final_smooth_window:
            prep.smooth(window=final_smooth_window, poly=smooth_polyorder)

        # 4. Normalization.
        self.normalization_method = normalize

        if normalize:
            if str(normalize).lower() in ("power_time", "power*time"):
                power = self.metadata.get("laser_power_mw", None)
                t = self.metadata.get("integration_time_s", None)
                prep.normalize("power_time", laser_power_mw=power, integration_time_s=t)
            else:
                prep.normalize(normalize)

        self.x = prep.x
        self.y = prep.y

        # Save reproducibility information.
        self.processing_recipe = recipe
        self.metadata["processing_recipe"] = json.dumps(recipe, sort_keys=True)
        self.metadata["n_spike_candidates"] = self.n_spike_candidates
        self.metadata["n_spikes_removed"] = self.n_spikes_removed

        return self

    def _axis_labels(self):
        xlabel = "Raman Shift (cm⁻¹)"
        norm = (self.normalization_method or "").lower() if self.normalization_method is not None else ""
        if norm in ("power_time", "power*time"):
            ylabel = "Intensity (ADU mW⁻¹ s⁻¹)"
        elif norm:
            ylabel = "Normalized Intensity (a.u.)"
        else:
            ylabel = "Intensity (a.u.)"
        return xlabel, ylabel

    def plot(self, xlim=(200, 2000), ylim=None, *, fontsize=12, linewidth=2.0, title=None):
        
        try:
            import matplotlib.pyplot as plt
        except ImportError as exc:
            raise ImportError(
                "Spectrum.plot() requires matplotlib. Install it with:\n"
                "python -m pip install matplotlib"
            ) from exc
            
        plt.figure(figsize=(10, 4.2))
        plt.plot(self.x, self.y, linewidth=float(linewidth))
        xlabel, ylabel = self._axis_labels()
        plt.xlabel(xlabel, fontsize=fontsize)
        plt.ylabel(ylabel, fontsize=fontsize)
        plt.tick_params(axis="both", labelsize=fontsize)
        if xlim:
            plt.xlim(*xlim)
        if ylim:
            plt.ylim(*ylim)
        if title:
            plt.title(title, fontsize=fontsize)
        plt.tight_layout()
        return plt.gca()

    def export_excel(
        self,
        out_path,
        *,
        include_chart=True,
        include_metadata=True,
        engine="auto",
        xlim=(200, 2000),
        y_lock=True,
        fontsize=12,
        chart_title_mode="blank",
        chart_title_text="",
        y_axis_label_override=None,
    ):
        """Compatibility wrapper for old Spectrum.export_excel calls."""
        from ecsers_analyzer.export.raman_excel import export_single_spectrum_excel

        return export_single_spectrum_excel(
            self,
            out_path,
            include_chart=include_chart,
            include_metadata=include_metadata,
            engine=engine,
            xlim=xlim,
            y_lock=y_lock,
            fontsize=fontsize,
            chart_title_mode=chart_title_mode,
            chart_title_text=chart_title_text,
            y_axis_label_override=y_axis_label_override,
        )



