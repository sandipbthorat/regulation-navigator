"""Build a structured, UI-neutral assessment from graph state."""

from __future__ import annotations

from typing import Any

from regulation_navigator.models import RegulatoryState

APPLICABILITY_NOTES = {
    "fda_device_definition": "Screens whether the intended software function meets the U.S. device definition.",
    "fdca_520o": "Screens statutory software-function exclusions.",
    "fda_device_software_policy": "Applies FDA's function-specific digital-health policy.",
    "fda_cds": "Screens the four Non-Device CDS criteria.",
    "fda_general_wellness": "Screens the current low-risk general-wellness policy.",
    "fda_mdds": "Screens whether the function is solely transfer/store/format/display.",
    "fda_premarket_software": "Identifies recommended device-software submission documentation.",
    "fda_ots": "Screens third-party and off-the-shelf software information needs.",
    "fda_cybersecurity": "Screens total-product-lifecycle cybersecurity considerations.",
    "fda_ai_lifecycle": "Flags draft AI lifecycle recommendations; not final guidance.",
    "fda_ai_pccp": "Screens whether planned AI changes could be addressed in a PCCP.",
    "fda_qmsr": "Screens binding manufacturer quality-system requirements under 21 CFR Part 820.",
    "iec_62304": "Screens the medical-device software lifecycle framework and preliminary safety class.",
    "iso_14971": "Connects software hazards and controls to device risk management.",
    "imdrf_n10": "Screens whether independent medical-purpose software meets the SaMD definition.",
    "imdrf_n12": "Screens the two-dimensional IMDRF SaMD impact category.",
    "imdrf_n23": "Flags SaMD quality-management principles.",
    "imdrf_n41": "Flags SaMD clinical-evaluation evidence dimensions.",
    "eu_mdr_rule11": "Screens EU MDR qualification, Rule 11, and applicable GSPRs.",
}


def compose_assessment(state: RegulatoryState) -> dict[str, Any]:
    evidence_by_key: dict[str, dict[str, Any]] = {}
    for item in state.get("citations", []):
        evidence_by_key.setdefault(item["source_key"], item)

    requirements = []
    for source_key in state.get("applicable_regulations", []):
        source = evidence_by_key.get(source_key, {})
        requirements.append(
            {
                "source_key": source_key,
                "authority": source.get("authority", "Evidence not retrieved"),
                "document": source.get("document", source_key),
                "section": source.get("section", "Review required"),
                "status": source.get("status", "Unknown"),
                "applicability": APPLICABILITY_NOTES.get(source_key, "Screen for applicability."),
                "citation": source.get("chunk_id", "missing"),
                "source_url": source.get("source_url", ""),
            }
        )

    assessment = {
        "answer_status": state.get("answer_status"),
        "narrative": state.get("narrative", ""),
        "classification": {
            "software_category": state.get("software_category"),
            "us_fda_status": state.get("us_device_status"),
            "cds_status": state.get("cds_status"),
            "imdrf_samd": state.get("samd_category"),
            "iec_62304": state.get("iec62304_class"),
            "eu_mdr": state.get("eu_mdr_class"),
        },
        "rationale": state.get("rationale", []),
        "applicable_requirements": requirements,
        "uncertainties": state.get("uncertainties", []),
        "follow_up_questions": state.get("follow_up_questions", []),
        "citation_validation": state.get("citation_validation", {}),
        "freshness_validation": state.get("freshness_validation", {}),
        "grounding": state.get("grounding", {}),
        "claims": state.get("claims", []),
        "evidence": state.get("citations", []),
        "disclaimer": (
            "Preliminary educational screening only—not legal advice, an FDA/EU classification decision, "
            "or a conformity assessment. Confirm the current official text, product claims, risk analysis, "
            "and jurisdiction-specific pathway with qualified regulatory professionals and authorities."
        ),
    }
    return {"assessment": assessment}
