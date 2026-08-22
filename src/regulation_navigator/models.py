"""Typed inputs and shared LangGraph state."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field

ConditionSeverity = Literal["critical", "serious", "non_serious", "unknown"]
InformationSignificance = Literal[
    "treat_or_diagnose", "drive_clinical_management", "inform_clinical_management", "unknown"
]
HazardSeverity = Literal["death_or_serious_injury", "non_serious_injury", "no_injury", "unknown"]
EUDecisionConsequence = Literal[
    "death_or_irreversible_deterioration",
    "serious_deterioration_or_surgical_intervention",
    "other",
    "unknown",
]
IntendedUser = Literal["clinician", "patient_or_caregiver", "manufacturer", "other", "unknown"]


class AssessmentInput(BaseModel):
    """Known facts about one software function.

    Unknown values deliberately remain ``None``/``unknown``. The navigator asks for
    the missing fact instead of forcing a regulatory conclusion.
    """

    model_config = ConfigDict(extra="forbid")

    software_description: str = Field(min_length=10, max_length=10_000)
    intended_use: str = ""
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


class EvidenceRecord(TypedDict, total=False):
    chunk_id: str
    authority: str
    jurisdiction: str
    document: str
    document_type: str
    status: str
    date: str
    section: str
    source_url: str
    text: str
    score: float
    source_key: str
    superseded: bool
    reviewed_at: str


class GroundedClaim(TypedDict, total=False):
    claim_id: str
    label: str
    text: str
    source_keys: list[str]
    citations: list[str]
    grounded: bool


class RegulatoryState(TypedDict, total=False):
    # Input and normalized facts
    input: dict[str, Any]
    facts: dict[str, Any]
    extraction_method: str
    # Deterministic classification outputs
    software_category: str
    us_device_status: str
    cds_status: str
    samd_category: str
    iec62304_class: str
    eu_mdr_class: str
    applicable_regulations: list[str]
    rationale: list[str]
    uncertainties: list[str]
    follow_up_questions: list[str]
    # Retrieval and grounding
    retrieval_queries: list[str]
    retrieved_sources: list[EvidenceRecord]
    citations: list[EvidenceRecord]
    citation_validation: dict[str, Any]
    freshness_validation: dict[str, Any]
    claims: list[GroundedClaim]
    narrative: str
    answer_status: str
    grounding: dict[str, Any]
    # Rendered response
    assessment: dict[str, Any]
