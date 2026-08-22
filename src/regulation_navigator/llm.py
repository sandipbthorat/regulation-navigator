"""Optional LLM-assisted fact extraction with deterministic fallback."""

from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, ConfigDict

from regulation_navigator.config import Settings
from regulation_navigator.models import (
    ConditionSeverity,
    EUDecisionConsequence,
    HazardSeverity,
    InformationSignificance,
    IntendedUser,
    RegulatoryState,
)
from regulation_navigator.prompts import FACT_EXTRACTION_SYSTEM, FACT_EXTRACTION_USER
from regulation_navigator.rules import normalize_input


class ExtractedFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    medical_purpose: bool | None = None
    part_of_medical_device: bool | None = None
    standalone: bool | None = None
    cds: bool | None = None
    data_only: bool | None = None
    ai_ml: bool | None = None
    network_connected: bool | None = None
    controls_hardware_device: bool | None = None
    intended_user: IntendedUser = "unknown"
    hcp_can_independently_review_basis: bool | None = None
    provides_specific_output_or_directive: bool | None = None
    analyzes_medical_image_or_signal: bool | None = None
    information_significance: InformationSignificance = "unknown"
    condition_severity: ConditionSeverity = "unknown"
    hazard_severity: HazardSeverity = "unknown"
    eu_decision_consequence: EUDecisionConsequence = "unknown"


def _merge_missing(original: dict[str, Any], extracted: ExtractedFacts) -> dict[str, Any]:
    merged = dict(original)
    for key, value in extracted.model_dump().items():
        current = merged.get(key)
        if current is None and value is not None or current == "unknown" and value != "unknown":
            merged[key] = value
    return merged


def extract_facts(state: RegulatoryState) -> dict[str, Any]:
    settings = Settings.from_env()
    if not settings.use_llm or not os.getenv("OPENAI_API_KEY"):
        return normalize_input(state)

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI

        structured_model = ChatOpenAI(model=settings.model, temperature=0).with_structured_output(
            ExtractedFacts,
            method="json_schema",
        )
        source = state.get("input", {})
        extracted = structured_model.invoke(
            [
                SystemMessage(content=FACT_EXTRACTION_SYSTEM),
                HumanMessage(
                    content=FACT_EXTRACTION_USER.format(
                        software_description=source.get("software_description", ""),
                        intended_use=source.get("intended_use", ""),
                    )
                ),
            ]
        )
        normalized = normalize_input({"input": _merge_missing(source, extracted)})
        normalized["extraction_method"] = (
            f"structured LLM extraction ({settings.model}) + deterministic normalization"
        )
        return normalized
    except Exception as exc:  # noqa: BLE001 - model/provider failures must use the local fallback.
        normalized = normalize_input(state)
        normalized["extraction_method"] = (
            f"deterministic fallback after LLM extraction error ({type(exc).__name__})"
        )
        return normalized
