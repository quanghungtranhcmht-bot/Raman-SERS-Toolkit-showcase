from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ecsers_analyzer.processing.pipeline import process_spectrum
from ecsers_analyzer.processing.advisor import recommend_recipe
from ecsers_analyzer.processing.form import (
    ProcessingFormValues,
    ProcessingRecipePlan,
    build_processing_recipe_from_form,
)
from ecsers_analyzer.domain.recipe import ProcessingRecipe


@dataclass(frozen=True)
class ProcessingRunResult:
    ok: bool
    processed_spec: Any = None
    error_title: str = ""
    error_message: str = ""


@dataclass(frozen=True)
class AdvisorServiceResult:
    ok: bool
    recommendation: Any = None
    error_title: str = ""
    error_message: str = ""


class ProcessingService:
    """Backend service for processing workflows.

    This service must not import PySide6 or own any GUI behavior.
    The Qt frontend handles dialogs, widgets, and message boxes.
    """

    def build_recipe_from_form(
        self,
        form: ProcessingFormValues,
        *,
        raw_spec: Any = None,
        provided_integration_time_s: float | None = None,
    ) -> ProcessingRecipePlan:
        return build_processing_recipe_from_form(
            form,
            raw_spec=raw_spec,
            provided_integration_time_s=provided_integration_time_s,
        )

    def process_single(
        self,
        *,
        raw_spec: Any,
        recipe: ProcessingRecipe,
    ) -> ProcessingRunResult:
        if raw_spec is None:
            return ProcessingRunResult(
                ok=False,
                error_title="No spectrum",
                error_message="Open a spectrum first.",
            )

        if recipe is None:
            return ProcessingRunResult(
                ok=False,
                error_title="No recipe",
                error_message="Processing recipe is missing.",
            )

        try:
            processed = process_spectrum(raw_spec, recipe)
        except Exception as exc:
            return ProcessingRunResult(
                ok=False,
                error_title="Processing failed",
                error_message=str(exc),
            )

        return ProcessingRunResult(
            ok=True,
            processed_spec=processed,
        )

    def recommend_processing(
        self,
        *,
        raw_spec: Any,
        purpose: str = "plot",
    ) -> AdvisorServiceResult:
        if raw_spec is None:
            return AdvisorServiceResult(
                ok=False,
                error_title="No spectrum",
                error_message="Open a spectrum or select a batch folder first.",
            )

        try:
            recommendation = recommend_recipe(raw_spec, purpose=purpose)
        except Exception as exc:
            return AdvisorServiceResult(
                ok=False,
                error_title="Recommendation failed",
                error_message=str(exc),
            )

        return AdvisorServiceResult(
            ok=True,
            recommendation=recommendation,
        )