"""Command-line interface for assessment and ingestion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from regulation_navigator.freshness import audit_corpus_freshness
from regulation_navigator.graph import run_assessment
from regulation_navigator.ingest import SourceMetadata, ingest_path, write_jsonl
from regulation_navigator.models import AssessmentInput


def _tri_bool(value: str):
    return {"yes": True, "no": False, "unknown": None}[value]


def _assessment_parser(subparsers) -> None:
    parser = subparsers.add_parser("assess", help="Run a preliminary regulatory assessment")
    parser.add_argument("--description", required=True)
    parser.add_argument("--intended-use", default="")
    for field in (
        "medical-purpose",
        "part-of-medical-device",
        "standalone",
        "cds",
        "data-only",
        "ai-ml",
        "network-connected",
        "controls-hardware-device",
        "hcp-can-independently-review-basis",
        "provides-specific-output-or-directive",
        "analyzes-medical-image-or-signal",
    ):
        parser.add_argument(f"--{field}", choices=["yes", "no", "unknown"], default="unknown")
    parser.add_argument(
        "--intended-user",
        choices=["clinician", "patient_or_caregiver", "manufacturer", "other", "unknown"],
        default="unknown",
    )
    parser.add_argument(
        "--information-significance",
        choices=[
            "treat_or_diagnose",
            "drive_clinical_management",
            "inform_clinical_management",
            "unknown",
        ],
        default="unknown",
    )
    parser.add_argument(
        "--condition-severity",
        choices=["critical", "serious", "non_serious", "unknown"],
        default="unknown",
    )
    parser.add_argument(
        "--hazard-severity",
        choices=["death_or_serious_injury", "non_serious_injury", "no_injury", "unknown"],
        default="unknown",
    )
    parser.add_argument(
        "--eu-decision-consequence",
        choices=[
            "death_or_irreversible_deterioration",
            "serious_deterioration_or_surgical_intervention",
            "other",
            "unknown",
        ],
        default="unknown",
    )


def _ingestion_parser(subparsers) -> None:
    parser = subparsers.add_parser("ingest", help="Chunk an authorized PDF/Markdown/text source")
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--jurisdiction", required=True)
    parser.add_argument("--authority", required=True)
    parser.add_argument("--document-type", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--date", required=True, help="Source issue/effective date")
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--source-key", required=True)
    parser.add_argument("--superseded", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="regnav")
    subparsers = parser.add_subparsers(dest="command", required=True)
    _assessment_parser(subparsers)
    _ingestion_parser(subparsers)
    subparsers.add_parser("audit-corpus", help="Check corpus review cadence and freshness SLA")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "audit-corpus":
        print(json.dumps(audit_corpus_freshness(), indent=2))
        return
    if args.command == "ingest":
        metadata = SourceMetadata(
            jurisdiction=args.jurisdiction,
            authority=args.authority,
            document_type=args.document_type,
            status=args.status,
            date=args.date,
            source_url=args.source_url,
            source_key=args.source_key,
            superseded=args.superseded,
        )
        records = ingest_path(args.path, metadata)
        write_jsonl(records, args.output)
        print(json.dumps({"output": str(args.output), "chunks": len(records)}, indent=2))
        return

    bool_fields = (
        "medical_purpose",
        "part_of_medical_device",
        "standalone",
        "cds",
        "data_only",
        "ai_ml",
        "network_connected",
        "controls_hardware_device",
        "hcp_can_independently_review_basis",
        "provides_specific_output_or_directive",
        "analyzes_medical_image_or_signal",
    )
    payload = {
        "software_description": args.description,
        "intended_use": args.intended_use,
        "intended_user": args.intended_user,
        "information_significance": args.information_significance,
        "condition_severity": args.condition_severity,
        "hazard_severity": args.hazard_severity,
        "eu_decision_consequence": args.eu_decision_consequence,
    }
    for field in bool_fields:
        payload[field] = _tri_bool(getattr(args, field))
    result = run_assessment(AssessmentInput.model_validate(payload))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
