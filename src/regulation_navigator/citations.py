"""Citation lifecycle validation and coverage metrics."""

from __future__ import annotations

from collections import Counter
from typing import Any

from regulation_navigator.models import RegulatoryState


def validate_citations(state: RegulatoryState) -> dict[str, Any]:
    evidence = state.get("retrieved_sources", [])
    valid = [
        item
        for item in evidence
        if item.get("source_url", "").startswith("https://")
        and item.get("section")
        and item.get("document")
        and not item.get("superseded", False)
    ]
    expected = set(state.get("applicable_regulations", []))
    present = {item.get("source_key") for item in valid}
    covered = expected.intersection(present)
    coverage = len(covered) / len(expected) if expected else 1.0
    status_counts = Counter(item.get("status", "Unknown") for item in valid)
    warnings: list[str] = []
    if any("Draft" in status for status in status_counts):
        warnings.append(
            "Draft guidance is present and must not be represented as final or binding."
        )
    licensed = [item for item in valid if "licensed" in item.get("document_type", "").lower()]
    if licensed:
        warnings.append(
            "IEC/ISO evidence is catalog-level; consult licensed standards for clause-level conclusions."
        )
    missing = sorted(expected.difference(present))
    if missing:
        warnings.append("No validated evidence was retrieved for: " + ", ".join(missing))

    return {
        "citations": valid,
        "citation_validation": {
            "valid_citation_count": len(valid),
            "applicability_source_coverage": round(coverage, 3),
            "covered_source_keys": sorted(covered),
            "missing_source_keys": missing,
            "status_counts": dict(status_counts),
            "warnings": warnings,
        },
    }
