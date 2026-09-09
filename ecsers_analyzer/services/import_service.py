from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ecsers_analyzer.io.csv_loader import load_csv_spectrum
from ecsers_analyzer.io.vendor_importers import load_spe_spectrum, load_paax_traces


SUPPORTED_SPECTRAL_EXTENSIONS = {".csv", ".spe"}
DEFAULT_LASER_POWER_MW = 34.1


@dataclass(frozen=True)
class SpectrumLoadResult:
    ok: bool
    spectrum: Any = None
    path: Path | None = None
    error_title: str = ""
    error_message: str = ""


@dataclass(frozen=True)
class PaaxLoadResult:
    ok: bool
    traces: list[Any] | None = None
    path: Path | None = None
    error_title: str = ""
    error_message: str = ""


class ImportService:
    """Backend service for file import/discovery.

    This service intentionally has no PySide6 imports.
    The Qt UI handles dialogs and widget updates.
    """

    def is_supported_spectral_file(self, path: str | Path) -> bool:
        p = Path(path)
        return (
            p.is_file()
            and p.suffix.lower() in SUPPORTED_SPECTRAL_EXTENSIONS
            and p.name.lower() != "metadata.csv"
        )

    def discover_spectral_files(self, folder: str | Path) -> list[Path]:
        folder = Path(folder)

        direct = sorted(
            p for p in folder.iterdir()
            if self.is_supported_spectral_file(p)
        )

        if direct:
            return direct

        return sorted(
            p for p in folder.rglob("*")
            if self.is_supported_spectral_file(p)
        )

    def display_name(self, path: str | Path, base_folder: str | Path | None = None) -> str:
        p = Path(path)

        if base_folder is not None:
            try:
                return str(p.relative_to(Path(base_folder)))
            except Exception:
                pass

        return p.name

    def load_spectrum_file(
        self,
        path: str | Path,
        *,
        laser_power_mw: float | None = None,
    ) -> SpectrumLoadResult:
        p = Path(path)
        suffix = p.suffix.lower()

        if laser_power_mw is None:
            laser_power_mw = DEFAULT_LASER_POWER_MW

        try:
            if suffix == ".spe":
                spec = load_spe_spectrum(str(p), laser_power_mw=laser_power_mw)
            elif suffix == ".csv":
                spec = load_csv_spectrum(str(p), laser_power_mw=laser_power_mw)
            else:
                return SpectrumLoadResult(
                    ok=False,
                    path=p,
                    error_title="Unsupported file",
                    error_message=f"Unsupported file type: {p.name}",
                )
        except Exception as exc:
            return SpectrumLoadResult(
                ok=False,
                path=p,
                error_title="Load failed",
                error_message=str(exc),
            )

        return SpectrumLoadResult(
            ok=True,
            spectrum=spec,
            path=p,
        )

    def load_paax_file(self, path: str | Path) -> PaaxLoadResult:
        p = Path(path)

        try:
            traces = list(load_paax_traces(p))
        except Exception as exc:
            return PaaxLoadResult(
                ok=False,
                path=p,
                error_title="PAAX import failed",
                error_message=str(exc),
            )

        if not traces:
            return PaaxLoadResult(
                ok=False,
                traces=[],
                path=p,
                error_title="No traces found",
                error_message="No electrochemical traces were found in this PAAX file.",
            )

        return PaaxLoadResult(
            ok=True,
            traces=traces,
            path=p,
        )