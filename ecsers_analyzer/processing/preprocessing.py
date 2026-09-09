import numpy as np
from scipy.signal import savgol_filter
from scipy.ndimage import median_filter
from scipy import sparse
from scipy.sparse.linalg import spsolve


def _mad(values):
    values = np.asarray(values, dtype=float)
    med = np.nanmedian(values)
    return np.nanmedian(np.abs(values - med))


def window_points_from_cm1(x, width_cm1, minimum=5):
    """Convert a smoothing width in cm⁻¹ into an odd Savitzky-Golay window.

    The minimum is intentionally small (5 points by default). Peak preservation
    takes priority over forcing a visually smoother trace.
    """
    x = np.asarray(x, dtype=float)

    if x.size < 3:
        return int(minimum)

    dx = np.nanmedian(np.abs(np.diff(np.sort(x))))

    if not np.isfinite(dx) or dx <= 0:
        return int(minimum)

    points = int(round(float(width_cm1) / dx))

    if points % 2 == 0:
        points += 1

    if points < minimum:
        points = minimum

    return points


def detect_cosmic_ray_masks(
    y,
    *,
    window=7,
    threshold=7.0,
    max_width_points=1,
):
    """Return ``(candidate_mask, accepted_mask)`` for conservative despiking.

    Candidates are *positive* local median-filter residuals above a robust MAD
    threshold. Contiguous candidate runs wider than ``max_width_points`` are
    preserved because they are more consistent with narrow Raman/SERS bands
    than isolated detector hits.

    This detector deliberately favors false negatives over deleting legitimate
    spectral peaks.
    """
    y = np.asarray(y, dtype=float)

    if not np.isfinite(y).all():
        raise ValueError("NaN/inf in spectrum before despiking.")

    window = int(window)
    if window % 2 == 0:
        window += 1
    if window < 3:
        window = 3

    max_width_points = max(1, int(max_width_points))

    empty = np.zeros_like(y, dtype=bool)
    if y.size < window:
        return empty.copy(), empty.copy()

    med = median_filter(y, size=window, mode="nearest")
    residual = y - med
    sigma = 1.4826 * _mad(residual)

    if not np.isfinite(sigma) or sigma <= 0:
        return empty.copy(), empty.copy()

    # Cosmic rays are modeled conservatively as positive detector excursions.
    candidate_mask = residual > float(threshold) * sigma
    accepted_mask = np.zeros_like(candidate_mask, dtype=bool)

    indices = np.flatnonzero(candidate_mask)
    if indices.size == 0:
        return candidate_mask, accepted_mask

    run_start = 0
    for pos in range(1, indices.size + 1):
        at_end = pos == indices.size
        run_break = (not at_end) and (indices[pos] != indices[pos - 1] + 1)
        if at_end or run_break:
            run = indices[run_start:pos]
            if run.size <= max_width_points:
                accepted_mask[run] = True
            run_start = pos

    return candidate_mask, accepted_mask


def _interpolate_masked_points(y, mask):
    """Linearly interpolate accepted spike points from unaffected neighbors."""
    y = np.asarray(y, dtype=float)
    mask = np.asarray(mask, dtype=bool)
    if not np.any(mask):
        return y.copy()

    good = ~mask
    if np.sum(good) < 2:
        return y.copy()

    idx = np.arange(y.size, dtype=float)
    out = y.copy()
    out[mask] = np.interp(idx[mask], idx[good], y[good])
    return out

class Preprocessor:
    def __init__(self, wavenumbers, intensities):
        self.x = np.asarray(wavenumbers, dtype=float)
        self.y = np.asarray(intensities, dtype=float)
        self.baseline_ = None
        self.spike_candidate_mask_ = None
        self.spike_mask_ = None
        self.n_spike_candidates_ = 0
        self.n_spikes_ = 0

    def despike_median(self, window=7, threshold=7.0, max_width_points=1):
        """Remove conservative, isolated positive cosmic-ray candidates.

        Multi-point candidate runs are preserved by default so narrow Raman/SERS
        bands are not flattened merely because they are intense. Accepted points
        are replaced by linear interpolation between unaffected neighbors.
        """
        y = np.asarray(self.y, dtype=float)

        candidate_mask, spike_mask = detect_cosmic_ray_masks(
            y,
            window=window,
            threshold=threshold,
            max_width_points=max_width_points,
        )

        self.y = _interpolate_masked_points(y, spike_mask)
        self.spike_candidate_mask_ = candidate_mask
        self.spike_mask_ = spike_mask
        self.n_spike_candidates_ = int(np.sum(candidate_mask))
        self.n_spikes_ = int(np.sum(spike_mask))
        return self
    
    def smooth(self, window=15, poly=2):
        if window is None:
            return self

        window = int(window)

        if window <= 0:
            return self

        poly = int(poly)

        if self.y.size < 5:
            return self

        if window % 2 == 0:
            window += 1

        if window < 5:
            window = 5

        # SavGol window cannot be larger than spectrum length.
        if window >= self.y.size:
            window = self.y.size - 1

        if window % 2 == 0:
            window -= 1

        if window < 5:
            return self

        if poly >= window:
            poly = window - 2

        if poly < 1:
            poly = 1

        self.y = savgol_filter(self.y, window_length=window, polyorder=poly)
        return self

    def normalize(self, method="max", *, laser_power_mw=None, integration_time_s=None):
        y = self.y
        if method is None:
            return self

        method = str(method).lower()
        if method == "max":
            denom = np.max(np.abs(y)) if np.max(np.abs(y)) != 0 else 1.0
            self.y = y / denom
        elif method in ("vector", "l2"):
            denom = np.linalg.norm(y)
            self.y = y / (denom if denom != 0 else 1.0)
        elif method == "area":
            denom = np.trapz(np.abs(y), self.x)
            self.y = y / (denom if denom != 0 else 1.0)
        elif method in ("power_time", "power*time"):
            if laser_power_mw is None or integration_time_s is None:
                raise ValueError("power_time normalization requires laser_power_mw and integration_time_s.")
            denom = float(laser_power_mw) * float(integration_time_s)
            self.y = y / (denom if denom != 0 else 1.0)
        else:
            raise ValueError(f"Unknown normalization method: {method}")
        return self

    def baseline_poly(self, order=3):
        order = int(order)
        coeffs = np.polyfit(self.x, self.y, order)
        baseline = np.polyval(coeffs, self.x)
        self.baseline_ = baseline
        self.y = self.y - baseline
        return self

    def baseline_als(self, lam=1e5, p=0.01, niter=10):
        y = self.y
        L = len(y)
        D = sparse.diags([1, -2, 1], [0, -1, -2], shape=(L, L-2)).T
        w = np.ones(L)
        for _ in range(int(niter)):
            W = sparse.spdiags(w, 0, L, L)
            Z = W + lam * (D @ D.T)
            z = spsolve(Z, w*y)
            w = p * (y > z) + (1-p) * (y < z)
        self.baseline_ = z
        self.y = y - z
        return self

    def baseline_airpls(self, lam=1e5, max_iter=80, tol=1e-3, w_min=1e-6, exp_clip=15.0):
        y = np.asarray(self.y, dtype=float)
        L = y.size
        if L < 3:
            self.baseline_ = np.zeros_like(y)
            self.y = y.copy()
            return self
        if not np.isfinite(y).all():
            raise ValueError("NaN/inf in spectrum before airPLS.")

        lam = float(lam)
        eps = 1e-12
        D = sparse.diags([1.0, -2.0, 1.0], [0, 1, 2], shape=(L-2, L), format="csc", dtype=float)
        w = np.ones(L, dtype=float)
        z = np.zeros(L, dtype=float)

        for i in range(int(max_iter)):
            W = sparse.diags(w, 0, shape=(L, L), format="csc")
            Z = W + lam * (D.T @ D)
            z = spsolve(Z, w * y)
            r = y - z
            neg = r < 0
            if not np.any(neg):
                break
            d = float(np.sum(np.abs(r[neg])))
            if d < tol:
                break
            w = np.full(L, float(w_min), dtype=float)
            v = (i + 1) * (np.abs(r[neg]) / (d + eps))
            v = np.clip(v, 0.0, float(exp_clip))
            w[neg] = np.exp(v)

        self.baseline_ = z
        self.y = y - z
        return self
