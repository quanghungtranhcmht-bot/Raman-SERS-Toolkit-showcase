from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ecsers_analyzer.export.raman_excel import (
    export_single_spectrum_excel,
    export_batch_excel,
)
from ecsers_analyzer.services.history_service import HistoryService

from ecsers_analyzer.export.paax_export import (
    export_paax_trace_csv,
    export_paax_trace_excel,
)




    

@dataclass(frozen=True)
class ExportResult:
    ok: bool
    output_path: Path | None = None
    status_message: str = ""
    error_title: str = ""
    error_message: str = ""


class ExportService:
    """Backend service for file export workflows.

    This service has no PySide6 dependency.
    The Qt frontend still owns file dialogs and message boxes.
    """

    def __init__(self, history_service: HistoryService | None = None):
        self.history_service = history_service or HistoryService()
    
    def export_single_raman(
        self,
        *,
        processed_spec: Any,
        out_path: str | Path,
        source_path: str | Path | None = None,
        raw_spec: Any = None,
        include_chart: bool = True,
        include_metadata: bool = True,
        engine: str = "auto",
        xlim: tuple[float, float] | None = None,
        y_lock: bool = True,
        fontsize: int = 12,
        chart_title_mode: str = "blank",
        chart_title_text: str = "",
        y_axis_label_override: str | None = None,
    ) -> ExportResult:
        if processed_spec is None:
            return ExportResult(
                ok=False,
                error_title="Nothing to export",
                error_message="Run Processing on a single CSV/SPE file first.",
            )

        out = Path(out_path)

        try:
            export_single_spectrum_excel(
                processed_spec,
                str(out),
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
        except Exception as exc:
            return ExportResult(
                ok=False,
                error_title="Export failed",
                error_message=str(exc),
            )

        self.history_service.log_export_single_excel(
            source_path=source_path,
            raw_spec=raw_spec,
            processed_spec=processed_spec,
        )

        return ExportResult(
            ok=True,
            output_path=out,
            status_message=f"Exported single Excel: {out}",
        )

    def export_batch_raman(
        self,
        *,
        batch_specs: list[Any],
        out_path: str | Path,
        processed_files: list[Path] | None = None,
        xlim: tuple[float, float] | None = None,
        batch_plot_mode: str = "overlay",
        stack_offset: float | None = None,
        y_lock: bool = True,
        fontsize: int = 12,
        chart_title_mode: str = "blank",
        chart_title_text: str = "",
        overlay_legend: bool = True,
        overlay_labels: list[str] | None = None,
        overlay_title: str | None = None,
        per_sheet_titles: list[str] | None = None,
        y_axis_label_override: str | None = None,
    ) -> ExportResult:
        if not batch_specs:
            return ExportResult(
                ok=False,
                error_title="Nothing to export",
                error_message="Run Batch Processing + Plot first.",
            )

        out = Path(out_path)

        try:
            export_batch_excel(
                batch_specs,
                str(out),
                xlim=xlim,
                batch_plot_mode=batch_plot_mode,
                stack_offset=stack_offset,
                y_lock=y_lock,
                fontsize=fontsize,
                chart_title_mode=chart_title_mode,
                chart_title_text=chart_title_text,
                overlay_legend=overlay_legend,
                overlay_labels=overlay_labels,
                overlay_title=overlay_title,
                per_sheet_titles=per_sheet_titles,
                y_axis_label_override=y_axis_label_override,
            )
        except Exception as exc:
            return ExportResult(
                ok=False,
                error_title="Export failed",
                error_message=str(exc),
            )

        for p, spec in zip(processed_files or [], batch_specs):
            self.history_service.log_export_batch_excel(
                source_path=p,
                processed_spec=spec,
            )

        return ExportResult(
            ok=True,
            output_path=out,
            status_message=f"Exported batch Excel: {out}",
        )

    def export_paax_csv(
        self,
        *,
        trace: Any,
        out_path: str | Path,
    ) -> ExportResult:
        if trace is None:
            return ExportResult(
                ok=False,
                error_title="No PAAX trace",
                error_message="Open a PAAX file and choose a trace first.",
            )

        out = Path(out_path)

        try:
            export_paax_trace_csv(trace, out)
        except Exception as exc:
            return ExportResult(
                ok=False,
                error_title="Export failed",
                error_message=str(exc),
            )

        return ExportResult(
            ok=True,
            output_path=out,
            status_message=f"Exported PAAX trace CSV: {out}",
        )

    def export_paax_excel(
        self,
        *,
        trace: Any,
        out_path: str | Path,
        source_path: str | Path | None = None,
    ) -> ExportResult:
        if trace is None:
            return ExportResult(
                ok=False,
                error_title="No PAAX trace",
                error_message="Open a PAAX file and choose a trace first.",
            )

        out = Path(out_path)

        try:
            export_paax_trace_excel(
                trace,
                out,
                source_path=source_path,
            )
        except ImportError as exc:
            return ExportResult(
                ok=False,
                error_title="Missing dependency",
                error_message=str(exc),
            )
        except ValueError as exc:
            return ExportResult(
                ok=False,
                error_title="Invalid trace",
                error_message=str(exc),
            )
        except Exception as exc:
            return ExportResult(
                ok=False,
                error_title="Export failed",
                error_message=str(exc),
            )

        return ExportResult(
            ok=True,
            output_path=out,
            status_message=f"Exported PAAX Excel: {out}",
        )
