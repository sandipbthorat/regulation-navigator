"""Deterministic regulatory decision nodes.

These are intentionally conservative screening rules, not legal conclusions. Each
node returns a partial LangGraph state update and can be unit-tested without an LLM.
"""

from __future__ import annotations

import re
from typing import Any

from regulation_navigator.models import RegulatoryState


def _contains(text: str, *phrases: str) -> bool:
    return any(
        re.search(rf"\b{re.escape(phrase)}\b", text, flags=re.IGNORECASE) for phrase in phrases
    )


def _description(facts: dict[str, Any]) -> str:
    return f"{facts.get('software_description', '')} {facts.get('intended_use', '')}".strip()


def normalize_input(state: RegulatoryState) -> dict[str, Any]:
    """Normalize user input and conservatively infer only obvious textual facts."""

    facts = dict(state.get("input", {}))
    text = _description(facts).lower()

    if facts.get("medical_purpose") is None:
        positive = _contains(
            text,
            "diagnose",
            "diagnosis",
            "treat",
            "treatment",
            "prevent disease",
            "mitigate",
            "patient-specific",
            "surgical",
            "clinical decision",
            "medical purpose",
        )
        wellness_only = (
            _contains(text, "general wellness", "fitness", "healthy lifestyle") and not positive
        )
        if positive:
            facts["medical_purpose"] = True
        elif wellness_only:
            facts["medical_purpose"] = False

    if facts.get("part_of_medical_device") is None and _contains(
        text, "embedded", "integrated into", "integral to", "surgical robot", "infusion pump"
    ):
        facts["part_of_medical_device"] = True

    if facts.get("standalone") is None:
        if facts.get("part_of_medical_device") is True:
            facts["standalone"] = False
        elif _contains(text, "standalone", "cloud application", "web application", "mobile app"):
            facts["standalone"] = True

    if facts.get("controls_hardware_device") is None and _contains(
        text, "controls", "changes settings", "commands", "actuates", "drives the device"
    ):
        facts["controls_hardware_device"] = True

    if facts.get("cds") is None and _contains(
        text,
        "clinical decision support",
        "recommendation",
        "treatment option",
        "alert to the surgeon",
    ):
        facts["cds"] = True

    if facts.get("data_only") is None:
        data_verbs = _contains(text, "transfer", "store", "display", "convert formats")
        transforms = _contains(
            text, "analyzes", "analyses", "diagnoses", "predicts", "controls", "recommends"
        )
        if data_verbs and _contains(text, "only", "solely") and not transforms:
            facts["data_only"] = True
        elif transforms:
            facts["data_only"] = False

    if facts.get("ai_ml") is None and _contains(
        text, "artificial intelligence", "machine learning", "deep learning", "neural network"
    ):
        facts["ai_ml"] = True

    if facts.get("network_connected") is None and _contains(
        text, "network-connected", "network connected", "internet-connected", "wireless", "cloud"
    ):
        facts["network_connected"] = True

    if facts.get("analyzes_medical_image_or_signal") is None and _contains(
        text, "medical image", "x-ray", "mri", "ct image", "ecg", "waveform", "sensor signal"
    ):
        facts["analyzes_medical_image_or_signal"] = _contains(
            text, "analyzes", "analyses", "processes", "interprets", "detects"
        )

    if facts.get("intended_user") == "unknown":
        if _contains(text, "surgeon", "physician", "clinician", "health care professional", "hcp"):
            facts["intended_user"] = "clinician"
        elif _contains(text, "patient", "caregiver", "consumer"):
            facts["intended_user"] = "patient_or_caregiver"
        elif _contains(text, "manufacturer", "production operator", "quality engineer"):
            facts["intended_user"] = "manufacturer"

    return {
        "facts": facts,
        "extraction_method": "deterministic keyword extraction + supplied facts",
    }


def classify_software_scope(state: RegulatoryState) -> dict[str, Any]:
    facts = state["facts"]
    text = _description(facts).lower()
    medical = facts.get("medical_purpose")
    rationale: list[str] = []

    is_non_product = _contains(
        text,
        "quality management system",
        "qms software",
        "manufacturing execution system",
        "production test station",
        "capa system",
        "complaint handling system",
    )

    if is_non_product:
        category = "Non-product/GxP or manufacturing software"
        rationale.append(
            "The described function supports the manufacturer or quality system rather than a patient-facing medical purpose."
        )
    elif medical is False and _contains(text, "general wellness", "fitness", "healthy lifestyle"):
        category = "General wellness software candidate"
        rationale.append(
            "The stated purpose is general wellness and no disease-specific medical purpose was identified."
        )
    elif facts.get("data_only") is True:
        category = "Data transfer/storage/display function candidate"
        rationale.append(
            "The function is stated to only transfer, store, convert, or display data without analysis or control."
        )
    elif facts.get("part_of_medical_device") is True:
        category = "Software in a Medical Device / Device Software Function candidate"
        rationale.append("The function is embedded in or integral to a hardware medical device.")
    elif facts.get("controls_hardware_device") is True:
        category = "Device software function or software accessory candidate"
        rationale.append(
            "Software that controls or changes the operation of a medical device may itself be a regulated device function."
        )
    elif facts.get("standalone") is True and medical is True:
        category = "Software as a Medical Device candidate"
        rationale.append(
            "The function has a medical purpose and is described as independent of medical-device hardware."
        )
    elif medical is True:
        category = "Device Software Function candidate; hardware relationship unresolved"
        rationale.append(
            "A medical purpose is present, but independence from hardware is not yet established."
        )
    elif medical is False:
        category = "Non-device software candidate"
        rationale.append("No medical purpose was identified from the supplied intended use.")
    else:
        category = "Indeterminate software function"
        rationale.append(
            "The intended use does not yet establish whether the function has a medical purpose."
        )

    return {"software_category": category, "rationale": rationale}


def analyze_us_status(state: RegulatoryState) -> dict[str, Any]:
    facts = state["facts"]
    category = state["software_category"]
    rationale = list(state.get("rationale", []))
    medical = facts.get("medical_purpose")
    cds_status = "Not identified as CDS"

    if category.startswith("Non-product/GxP"):
        us_status = "Not a device function on the supplied facts; QMS/validation controls may apply"
    elif category.startswith("General wellness"):
        us_status = "Potential non-device or enforcement-discretion general wellness function"
    elif facts.get("data_only") is True:
        us_status = "Potential non-device data function under FD&C Act §520(o)(1)(D)"
    elif facts.get("cds") is True:
        criteria = {
            "not_image_or_signal_analysis": facts.get("analyzes_medical_image_or_signal") is False,
            "hcp_user": facts.get("intended_user") == "clinician",
            "not_specific_directive": facts.get("provides_specific_output_or_directive") is False,
            "independent_review": facts.get("hcp_can_independently_review_basis") is True,
        }
        missing = [
            label
            for label, value in {
                "image/signal analysis": facts.get("analyzes_medical_image_or_signal"),
                "intended user": None if facts.get("intended_user") == "unknown" else True,
                "specific output/directive": facts.get("provides_specific_output_or_directive"),
                "independent review of basis": facts.get("hcp_can_independently_review_basis"),
            }.items()
            if value is None
        ]
        if all(criteria.values()):
            cds_status = (
                "Non-Device CDS candidate; all screened §520(o)(1)(E) criteria appear satisfied"
            )
            us_status = "Potential Non-Device CDS"
            rationale.append(
                "The screened CDS facts indicate an HCP recommendation whose basis can be independently reviewed and that does not analyze an image or signal."
            )
        elif missing:
            cds_status = "CDS identified; §520(o)(1)(E) determination needs additional facts"
            us_status = "Device status indeterminate pending CDS criteria"
        else:
            cds_status = (
                "Device CDS candidate; one or more screened §520(o)(1)(E) criteria are not met"
            )
            us_status = "Likely Device Software Function"
            rationale.append(
                "At least one screened Non-Device CDS criterion is not met; other FDA policies must still be considered."
            )
    elif medical is True or facts.get("controls_hardware_device") is True:
        us_status = "Likely Device Software Function"
    elif medical is False:
        us_status = "Likely outside the device definition on the supplied intended use"
    else:
        us_status = "Indeterminate — intended medical purpose required"

    return {"us_device_status": us_status, "cds_status": cds_status, "rationale": rationale}


def classify_imdrf_samd(state: RegulatoryState) -> dict[str, Any]:
    facts = state["facts"]
    if facts.get("medical_purpose") is not True:
        return {"samd_category": "Not applicable on current facts"}
    if (
        facts.get("part_of_medical_device") is True
        or facts.get("standalone") is False
        or facts.get("controls_hardware_device") is True
    ):
        return {
            "samd_category": "Not SaMD under IMDRF N10 because the function is part of or drives hardware"
        }
    if facts.get("standalone") is not True:
        return {"samd_category": "SaMD status unresolved — independence from hardware is unknown"}

    significance = facts.get("information_significance", "unknown")
    condition = facts.get("condition_severity", "unknown")
    matrix = {
        ("treat_or_diagnose", "critical"): "IV",
        ("treat_or_diagnose", "serious"): "III",
        ("treat_or_diagnose", "non_serious"): "II",
        ("drive_clinical_management", "critical"): "III",
        ("drive_clinical_management", "serious"): "II",
        ("drive_clinical_management", "non_serious"): "I",
        ("inform_clinical_management", "critical"): "II",
        ("inform_clinical_management", "serious"): "I",
        ("inform_clinical_management", "non_serious"): "I",
    }
    category = matrix.get((significance, condition))
    if category:
        return {"samd_category": f"Preliminary IMDRF SaMD Category {category} candidate"}
    return {
        "samd_category": "SaMD candidate; N12 category needs significance and condition severity"
    }


def classify_iec62304(state: RegulatoryState) -> dict[str, Any]:
    facts = state["facts"]
    if facts.get("medical_purpose") is not True and facts.get("part_of_medical_device") is not True:
        return {"iec62304_class": "Not applicable on current facts"}
    mapping = {
        "no_injury": "Preliminary IEC 62304 Class A candidate",
        "non_serious_injury": "Preliminary IEC 62304 Class B candidate",
        "death_or_serious_injury": "Preliminary IEC 62304 Class C candidate",
    }
    result = mapping.get(facts.get("hazard_severity"))
    if result:
        return {"iec62304_class": result}
    return {
        "iec62304_class": "Applicable framework; safety class requires software-hazard analysis"
    }


def classify_eu_mdr(state: RegulatoryState) -> dict[str, Any]:
    facts = state["facts"]
    if facts.get("medical_purpose") is False:
        return {"eu_mdr_class": "Likely outside MDR on the supplied intended use"}
    if facts.get("medical_purpose") is not True:
        return {"eu_mdr_class": "MDR qualification indeterminate — medical purpose required"}
    if facts.get("part_of_medical_device") is True or facts.get("controls_hardware_device") is True:
        return {
            "eu_mdr_class": "Rule 3.3/implementing rule screening needed; software may follow the driven device class"
        }

    hazard = facts.get("hazard_severity", "unknown")
    significance = facts.get("information_significance", "unknown")
    consequence = facts.get("eu_decision_consequence", "unknown")
    decision_information = significance in {
        "treat_or_diagnose",
        "drive_clinical_management",
        "inform_clinical_management",
    }
    if consequence == "death_or_irreversible_deterioration" and decision_information:
        return {"eu_mdr_class": "Preliminary MDR Rule 11 Class III candidate"}
    if consequence == "serious_deterioration_or_surgical_intervention" and decision_information:
        return {"eu_mdr_class": "Preliminary MDR Rule 11 Class IIb candidate"}
    if consequence == "other" and decision_information:
        return {"eu_mdr_class": "Preliminary MDR Rule 11 Class IIa candidate"}
    if hazard == "death_or_serious_injury" and decision_information:
        return {
            "eu_mdr_class": "Preliminary MDR Rule 11 Class IIb/III candidate; consequence details required"
        }
    if decision_information:
        return {
            "eu_mdr_class": "Preliminary MDR Rule 11 Class IIa candidate; consequence exceptions not assessed"
        }
    return {"eu_mdr_class": "Medical Device Software candidate; Rule 11 inputs incomplete"}


def collect_follow_up_questions(state: RegulatoryState) -> dict[str, Any]:
    facts = state["facts"]
    questions: list[str] = []
    uncertainties: list[str] = []

    def ask(condition: bool, question: str, uncertainty: str) -> None:
        if condition:
            questions.append(question)
            uncertainties.append(uncertainty)

    ask(
        facts.get("medical_purpose") is None,
        "What exact diagnosis, prevention, monitoring, prediction, prognosis, treatment, or mitigation claim is intended?",
        "The intended medical purpose is not established.",
    )
    ask(
        facts.get("medical_purpose") is True
        and facts.get("standalone") is None
        and facts.get("part_of_medical_device") is None,
        "Can the function achieve its medical purpose independently of medical-device hardware?",
        "The SaMD versus embedded/integral software boundary is unresolved.",
    )
    if facts.get("cds") is True:
        ask(
            facts.get("intended_user") == "unknown",
            "Is the output intended for a health care professional, a patient/caregiver, or both?",
            "The intended CDS user is unknown.",
        )
        ask(
            facts.get("analyzes_medical_image_or_signal") is None,
            "Does the function acquire, process, or analyze a medical image, signal, or pattern?",
            "CDS image/signal analysis status is unknown.",
        )
        ask(
            facts.get("provides_specific_output_or_directive") is None,
            "Does it provide options/recommendations, or a specific diagnostic or treatment output/directive?",
            "The specificity of the CDS output is unknown.",
        )
        ask(
            facts.get("hcp_can_independently_review_basis") is None,
            "Can the health care professional independently review the basis for every recommendation?",
            "Independent review of the CDS basis is unknown.",
        )
    ask(
        facts.get("medical_purpose") is True and facts.get("hazard_severity") == "unknown",
        "What is the worst reasonably foreseeable harm if this software fails or provides incorrect output?",
        "IEC 62304 safety class and EU Rule 11 consequences cannot be screened without hazard severity.",
    )
    ask(
        facts.get("medical_purpose") is True
        and facts.get("information_significance") != "unknown"
        and facts.get("eu_decision_consequence") == "unknown",
        "For an incorrect EU diagnostic or therapeutic decision, could the consequence be death/irreversible deterioration, serious deterioration/surgical intervention, or neither?",
        "The EU MDR Rule 11 IIa/IIb/III consequence exception is not fully resolved.",
    )
    ask(
        facts.get("standalone") is True
        and facts.get("medical_purpose") is True
        and facts.get("information_significance") == "unknown",
        "Does the output treat/diagnose, drive clinical management, or only inform clinical management?",
        "The IMDRF information-significance dimension is unknown.",
    )
    ask(
        facts.get("standalone") is True
        and facts.get("medical_purpose") is True
        and facts.get("condition_severity") == "unknown",
        "Is the target health-care situation or condition critical, serious, or non-serious?",
        "The IMDRF health-care-condition dimension is unknown.",
    )
    ask(
        facts.get("medical_purpose") is True and facts.get("network_connected") is None,
        "Does the function include network, wireless, cloud, update, or other cybersecurity-relevant connectivity?",
        "Cybersecurity applicability has not been fully screened.",
    )
    ask(
        facts.get("medical_purpose") is True and facts.get("ai_ml") is None,
        "Does the function use AI/ML, and can its model or performance change after release?",
        "AI lifecycle and PCCP applicability has not been fully screened.",
    )

    return {"follow_up_questions": questions, "uncertainties": uncertainties}


def determine_applicability(state: RegulatoryState) -> dict[str, Any]:
    facts = state["facts"]
    text = _description(facts).lower()
    regs = ["fda_device_definition"]
    status = state["us_device_status"]

    if facts.get("medical_purpose") is True or "Device" in status:
        regs.extend(["fda_device_software_policy", "eu_mdr_rule11", "iso_14971", "iec_62304"])
    if "Likely Device Software Function" in status:
        regs.extend(["fda_premarket_software", "fda_qmsr"])
    if facts.get("cds") is True:
        regs.extend(["fdca_520o", "fda_cds"])
    if facts.get("data_only") is True:
        regs.extend(["fdca_520o", "fda_mdds"])
    if state["software_category"].startswith("General wellness"):
        regs.extend(["fdca_520o", "fda_general_wellness"])
    if facts.get("standalone") is True and facts.get("medical_purpose") is True:
        regs.extend(["imdrf_n10", "imdrf_n12", "imdrf_n23", "imdrf_n41"])
    likely_device = status == "Likely Device Software Function"
    if facts.get("ai_ml") is True and likely_device:
        regs.extend(["fda_ai_lifecycle", "fda_ai_pccp"])
    if facts.get("network_connected") is True and likely_device:
        regs.append("fda_cybersecurity")
    if _contains(text, "off-the-shelf", "ots software", "windows", "linux", "third-party library"):
        regs.append("fda_ots")
    if state["software_category"].startswith("Non-product/GxP"):
        regs.append("fda_qmsr")

    return {"applicable_regulations": list(dict.fromkeys(regs))}
