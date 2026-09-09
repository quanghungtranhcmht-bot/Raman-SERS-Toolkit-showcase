from __future__ import annotations

from pathlib import Path
from typing import Any

from ecsers_analyzer.persistence.user_history import log_processing_event


class HistoryService:
    """Service boundary for local user-history logging.

    This service intentionally preserves the existing JSONL schema.
    Logging failures should never crash the scientific workflow.
    """

    def log_event(
        self,
        *,
        source_path: str | Path | None = None,
        raw_spec: Any = None,
        processed_spec: Any = None,
        recipe: Any = None,
        action: str,
        notes: str = "",
    ) -> bool:
        try:
            log_processing_event(
                source_path=source_path,
                raw_spec=raw_spec,
                processed_spec=processed_spec,
                recipe=recipe,
                action=action,
                notes=notes,
            )
            return True
        except Exception:
            return False

    def log_single_processed(
        self,
        *,
        source_path: str | Path | None,
        raw_spec: Any,
        processed_spec: Any,
    ) -> bool:
        return self.log_event(
            source_path=source_path,
            raw_spec=raw_spec,
            processed_spec=processed_spec,
            action="single_processed",
        )

    def log_batch_processed(
        self,
        *,
        source_path: str | Path | None,
        processed_spec: Any,
        notes: str = "",
    ) -> bool:
        return self.log_event(
            source_path=source_path,
            raw_spec=None,
            processed_spec=processed_spec,
            action="batch_processed",
            notes=notes,
        )

    def log_export_single_excel(
        self,
        *,
        source_path: str | Path | None,
        raw_spec: Any,
        processed_spec: Any,
    ) -> bool:
        return self.log_event(
            source_path=source_path,
            raw_spec=raw_spec,
            processed_spec=processed_spec,
            action="export_single_excel",
        )

    def log_export_batch_excel(
        self,
        *,
        source_path: str | Path | None,
        processed_spec: Any,
    ) -> bool:
        return self.log_event(
            source_path=source_path,
            raw_spec=None,
            processed_spec=processed_spec,
            action="export_batch_excel",
        )

    def log_advisor_decision(
        self,
        *,
        decision: str,
        source_path: str | Path | None,
        raw_spec: Any,
        processed_spec: Any,
        recipe: Any,
        notes: str = "",
    ) -> bool:
        decision = str(decision or "").strip().lower()

        if decision == "accepted":
            action = "advisor_accepted"
        elif decision == "rejected":
            action = "advisor_rejected"
        else:
            action = f"advisor_{decision or 'unknown'}"

        return self.log_event(
            source_path=source_path,
            raw_spec=raw_spec,
            processed_spec=processed_spec,
            recipe=recipe,
            action=action,
            notes=notes,
        )

    def log_library_reference_added(
        self,
        *,
        source_path: str | Path | None,
        raw_spec: Any,
        processed_spec: Any,
        notes: str = "",
    ) -> bool:
        return self.log_event(
            source_path=source_path,
            raw_spec=raw_spec,
            processed_spec=processed_spec,
            action="library_reference_added",
            notes=notes,
        )

    def log_library_search(
        self,
        *,
        source_path: str | Path | None,
        raw_spec: Any,
        processed_spec: Any,
        notes: str = "",
    ) -> bool:
        return self.log_event(
            source_path=source_path,
            raw_spec=raw_spec,
            processed_spec=processed_spec,
            action="library_search",
            notes=notes,
        )