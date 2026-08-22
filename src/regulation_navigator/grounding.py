"""Turn deterministic classifications into citation-bound atomic claims."""

from __future__ import annotations

import re
from typing import Any

from regulation_navigator.freshness import audit_corpus_freshness
from regulation_navigator.models import GroundedClaim, RegulatoryState

DOMAIN_TERMS = {
    "medical",
    "device",
    "software",
    "clinical",
    "patient",
    "diagnos",
    "treat",
    "health",
    "fda",
    "mdr",
    "samd",
    "iec",
    "regulat",
    "surgical",
    "qms",
    "capa",
    "manufactur",
}
OUT_OF_CORPUS_TERMS = {
    "cpt code",
    "reimbursement",
    "hipaa",
    "medical billing",
    "drug dosage",
    "veterinary drug",
}


def query_is_in_scope(text: str) -> bool:
    normalized = text.lower()
    return not any(term in normalized for term in OUT_OF_CORPUS_TERMS) and any(
        term in normalized for term in DOMAIN_TERMS
    )


def _category_sources(category: str) -> list[str]:
    if category.startswith("General wellness"):
        return ["fda_device_definition", "fdca_520o", "fda_general_wellness"]
    if category.startswith("Data transfer"):
        return ["fdca_520o", "fda_mdds"]
    if category.startswith("Non-product/GxP"):
        return ["fda_qmsr"]
    if "Software as a Medical Device" in category:
        return ["fda_device_definition", "imdrf_n10"]
    if "Medical Device" in category or "accessory" in category:
        return ["fda_device_definition", "fda_device_software_policy"]
    return ["fda_device_definition"]


def _us_sources(status: str, cds_status: str) -> list[str]:
    if "CDS" in status or not cds_status.startswith("Not identified"):
        return ["fdca_520o", "fda_cds"]
    if "general wellness" in status:
        return ["fdca_520o", "fda_general_wellness"]
    if "data function" in status:
        return ["fdca_520o", "fda_mdds"]
    if "QMS" in status:
        return ["fda_qmsr"]
    return ["fda_device_definition", "fda_device_software_policy"]


def _make_claim(
    claim_id: str,
    label: str,
    text: str,
    source_keys: list[str],
    evidence_by_key: dict[str, dict[str, Any]],
) -> GroundedClaim:
    citations = [evidence_by_key[key]["chunk_id"] for key in source_keys if key in evidence_by_key]
    return {
        "claim_id": claim_id,
        "label": label,
        "text": text,
        "source_keys": source_keys,
        "citations": list(dict.fromkeys(citations)),
        "grounded": bool(source_keys) and all(key in evidence_by_key for key in source_keys),
    }


def build_grounded_answer(state: RegulatoryState) -> dict[str, Any]:
    evidence_by_key: dict[str, dict[str, Any]] = {}
    for item in state.get("citations", []):
        evidence_by_key.setdefault(item["source_key"], item)

    claims = [
        _make_claim(
            "software-category",
            "Software category",
            state["software_category"],
            _category_sources(state["software_category"]),
            evidence_by_key,
        ),
        _make_claim(
            "us-status",
            "U.S. FDA status",
            state["us_device_status"],
            _us_sources(state["us_device_status"], state["cds_status"]),
            evidence_by_key,
        ),
        _make_claim(
            "imdrf",
            "IMDRF SaMD",
            state["samd_category"],
            ["imdrf_n10"] + (["imdrf_n12"] if "Category" in state["samd_category"] else []),
            evidence_by_key,
        ),
        _make_claim(
            "iec-62304",
            "IEC 62304",
            state["iec62304_class"],
            ["iec_62304"],
            evidence_by_key,
        ),
        _make_claim(
            "eu-mdr",
            "EU MDR",
            state["eu_mdr_class"],
            ["eu_mdr_rule11"],
            evidence_by_key,
        ),
    ]
    grounded_count = sum(claim["grounded"] for claim in claims)
    coverage = grounded_count / len(claims)
    facts = state["facts"]
    in_scope = query_is_in_scope(
        f"{facts.get('software_description', '')} {facts.get('intended_use', '')}"
    )
    freshness = audit_corpus_freshness()

    if not in_scope:
        answer_status = "refused_out_of_scope"
        narrative = (
            "I can’t support this request from the medical-device software regulatory corpus. "
            "Describe one software function, its intended user and medical purpose, or consult an "
            "appropriate source for the unrelated topic."
        )
    elif coverage < 0.8 or freshness["status"] != "current":
        answer_status = "refused_insufficient_evidence"
        narrative = (
            "I can’t provide a source-grounded assessment because the evidence coverage or corpus "
            "freshness check did not meet the release threshold. Review the listed missing evidence "
            "and refresh the corpus before relying on a classification."
        )
    else:
        answer_status = (
            "answer_with_caveats" if state.get("follow_up_questions") else "grounded_answer"
        )
        lines = ["Preliminary, source-grounded assessment:"]
        for claim in claims:
            citation_text = " ".join(f"[{citation}]" for citation in claim["citations"])
            lines.append(f"- {claim['label']}: {claim['text']} {citation_text}".rstrip())
        if state.get("follow_up_questions"):
            lines.append(
                "The result remains conditional because material facts are unresolved; answer the "
                "follow-up questions before using it for a regulatory decision."
            )
        narrative = "\n".join(lines)

    cited_ids = set(re.findall(r"\[([^\]]+)\]", narrative))
    valid_ids = {item["chunk_id"] for item in state.get("citations", [])}
    invalid_inline = sorted(cited_ids.difference(valid_ids))
    return {
        "claims": claims,
        "narrative": narrative,
        "answer_status": answer_status,
        "freshness_validation": freshness,
        "grounding": {
            "claim_count": len(claims),
            "grounded_claim_count": grounded_count,
            "claim_level_faithfulness": round(coverage, 3),
            "invalid_inline_citations": invalid_inline,
            "release_threshold": 0.8,
        },
    }
