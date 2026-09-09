from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ecsers_analyzer.library.spectral_library import add_reference_spectrum
from ecsers_analyzer.library.search import search_library
from ecsers_analyzer.library.workflow import (
    add_reference_kwargs,
    add_reference_log_notes,
    added_reference_message,
    added_reference_status,
    build_reference_input_plan,
    can_search_library,
    search_result_table_rows,
    search_status_message,
)
from ecsers_analyzer.services.history_service import HistoryService

@dataclass(frozen=True)
class LibraryAddResult:
    ok: bool
    row: dict | None = None
    compound_name: str = ""
    status_message: str = ""
    user_message: str = ""
    error_title: str = ""
    error_message: str = ""


@dataclass(frozen=True)
class LibrarySearchResult:
    ok: bool
    results: list[dict] | None = None
    table_rows: list[list[str]] | None = None
    status_message: str = ""
    error_title: str = ""
    error_message: str = ""


class LibraryService:
    """Backend service for SERS library workflows.

    This class intentionally has no PySide6 imports.
    The Qt UI can call this service, then display results in widgets.
    """

    def __init__(self, history_service: HistoryService | None = None):
        self.history_service = history_service or HistoryService()
    def add_reference(
        self,
        *,
        processed_spec: Any,
        raw_spec: Any = None,
        source_path: str | Path | None = None,
        compound_text: Any,
        concentration_text: Any,
        notes_text: Any,
    ) -> LibraryAddResult:
        plan = build_reference_input_plan(
            processed_spec=processed_spec,
            compound_text=compound_text,
            concentration_text=concentration_text,
            notes_text=notes_text,
        )

        if not plan.ok:
            return LibraryAddResult(
                ok=False,
                error_title=plan.error_title,
                error_message=plan.error_message,
            )

        try:
            row = add_reference_spectrum(
                processed_spec,
                **add_reference_kwargs(plan),
            )
        except Exception as exc:
            return LibraryAddResult(
                ok=False,
                error_title="Library save failed",
                error_message=str(exc),
            )

        self.history_service.log_library_reference_added(
            source_path=source_path,
            raw_spec=raw_spec,
            processed_spec=processed_spec,
            notes=add_reference_log_notes(plan),
        )

        return LibraryAddResult(
            ok=True,
            row=row,
            compound_name=plan.compound_name,
            status_message=added_reference_status(row, plan.compound_name),
            user_message=added_reference_message(plan.compound_name),
        )

    def search_unknown(
        self,
        *,
        processed_spec: Any,
        raw_spec: Any = None,
        source_path: str | Path | None = None,
        xlim: tuple[float, float] | None = None,
        top_n: int = 10,
    ) -> LibrarySearchResult:
        ok, title, message = can_search_library(processed_spec)

        if not ok:
            return LibrarySearchResult(
                ok=False,
                error_title=title,
                error_message=message,
            )

        try:
            results = search_library(
                processed_spec,
                xlim=xlim,
                top_n=top_n,
            )
        except Exception as exc:
            return LibrarySearchResult(
                ok=False,
                error_title="Library search failed",
                error_message=str(exc),
            )

        status = search_status_message(results)

        self.history_service.log_library_search(
            source_path=source_path,
            raw_spec=raw_spec,
            processed_spec=processed_spec,
            notes=f"top_n={top_n}; xlim={xlim}; results={len(results)}"
        )

        return LibrarySearchResult(
            ok=True,
            results=results,
            table_rows=search_result_table_rows(results),
            status_message=status,
        )