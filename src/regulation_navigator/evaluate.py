"""Evaluation-as-code for classification, grounding, retrieval, refusal, and latency."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import mean, median

from regulation_navigator.config import PROJECT_ROOT
from regulation_navigator.graph import run_assessment
from regulation_navigator.grounding import query_is_in_scope
from regulation_navigator.retrieval import get_retriever

GOLD_PATH = PROJECT_ROOT / "data" / "evals" / "gold_cases.jsonl"
RETRIEVAL_PATH = PROJECT_ROOT / "data" / "evals" / "retrieval_cases.jsonl"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "docs" / "EVALUATION_REPORT.md"


def load_cases(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def _ndcg(ranked: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 1.0
    dcg = sum(
        1 / math.log2(rank + 1)
        for rank, source_key in enumerate(ranked[:k], 1)
        if source_key in relevant
    )
    ideal_hits = min(len(relevant), k)
    ideal = sum(1 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / ideal if ideal else 1.0


def evaluate_classification(path: Path = GOLD_PATH) -> tuple[dict, list[dict]]:
    rows = []
    for case in load_cases(path):
        result = run_assessment(case["input"])
        expected = case["expected"]
        classification = result["classification"]
        category_ok = (
            expected["software_category_contains"].lower()
            in classification["software_category"].lower()
        )
        us_ok = expected["us_status_contains"].lower() in classification["us_fda_status"].lower()
        retrieved = {item["source_key"] for item in result["evidence"]}
        required = set(expected.get("required_source_keys", []))
        recall = len(retrieved.intersection(required)) / len(required) if required else 1.0
        validation = result["citation_validation"]
        citations_valid = validation["valid_citation_count"] == len(result["evidence"])
        grounding = result["grounding"]
        rows.append(
            {
                "id": case["id"],
                "category_correct": category_ok,
                "us_status_correct": us_ok,
                "required_source_recall": round(recall, 3),
                "citation_metadata_valid": citations_valid,
                "claim_level_faithfulness": grounding["claim_level_faithfulness"],
                "inline_citations_valid": not grounding["invalid_inline_citations"],
                "answer_released": not result["answer_status"].startswith("refused"),
                "latency_seconds": result["latency_seconds"],
            }
        )

    latencies = [row["latency_seconds"] for row in rows]
    summary = {
        "cases": len(rows),
        "software_category_accuracy": round(mean(row["category_correct"] for row in rows), 3),
        "us_status_accuracy": round(mean(row["us_status_correct"] for row in rows), 3),
        "required_source_recall": round(mean(row["required_source_recall"] for row in rows), 3),
        "citation_metadata_validity": round(
            mean(row["citation_metadata_valid"] for row in rows), 3
        ),
        "claim_level_faithfulness": round(mean(row["claim_level_faithfulness"] for row in rows), 3),
        "inline_citation_validity": round(mean(row["inline_citations_valid"] for row in rows), 3),
        "answer_release_rate": round(mean(row["answer_released"] for row in rows), 3),
        "latency_p50_seconds": round(median(latencies), 3),
        "latency_p95_seconds": round(_percentile(latencies, 0.95), 3),
        "latency_target_seconds": 5.0,
        "latency_target_met": _percentile(latencies, 0.95) <= 5.0,
    }
    return summary, rows


def evaluate_retrieval(path: Path = RETRIEVAL_PATH, k: int = 5) -> tuple[dict, list[dict]]:
    retriever = get_retriever()
    rows = []
    for case in load_cases(path):
        expected = set(case["expected_source_keys"])
        ranked = [item["source_key"] for item in retriever.search(case["query"], k=k)]
        unique_ranked = list(dict.fromkeys(ranked))
        should_refuse = case.get("should_refuse", False)
        refused = not query_is_in_scope(case["query"])
        if expected:
            recall = len(expected.intersection(unique_ranked)) / len(expected)
            reciprocal_rank = next(
                (1 / rank for rank, key in enumerate(unique_ranked, 1) if key in expected),
                0.0,
            )
        else:
            recall = 1.0 if refused else 0.0
            reciprocal_rank = 1.0 if refused else 0.0
        rows.append(
            {
                "id": case["id"],
                "recall_at_5": round(recall, 3),
                "reciprocal_rank": round(reciprocal_rank, 3),
                "ndcg_at_5": round(_ndcg(unique_ranked, expected, k), 3) if expected else recall,
                "refusal_correct": refused == should_refuse,
                "top_source_keys": unique_ranked,
            }
        )
    summary = {
        "cases": len(rows),
        "recall_at_5": round(mean(row["recall_at_5"] for row in rows), 3),
        "mrr": round(mean(row["reciprocal_rank"] for row in rows), 3),
        "ndcg_at_5": round(mean(row["ndcg_at_5"] for row in rows), 3),
        "refusal_accuracy": round(mean(row["refusal_correct"] for row in rows), 3),
    }
    return summary, rows


def evaluate(
    gold_path: Path = GOLD_PATH, retrieval_path: Path = RETRIEVAL_PATH
) -> dict[str, object]:
    classification_summary, classification_rows = evaluate_classification(gold_path)
    retrieval_summary, retrieval_rows = evaluate_retrieval(retrieval_path)
    failures = []
    for row in classification_rows:
        failed = [
            key
            for key in (
                "category_correct",
                "us_status_correct",
                "citation_metadata_valid",
                "inline_citations_valid",
                "answer_released",
            )
            if not row[key]
        ]
        if row["required_source_recall"] < 1 or row["claim_level_faithfulness"] < 0.95:
            failed.append("grounding_or_source_recall")
        if failed:
            failures.append({"id": row["id"], "failed_checks": failed})
    for row in retrieval_rows:
        failed = []
        if row["recall_at_5"] < 1:
            failed.append("retrieval_recall")
        if not row["refusal_correct"]:
            failed.append("refusal")
        if failed:
            failures.append({"id": row["id"], "failed_checks": failed})
    return {
        "classification_and_grounding": classification_summary,
        "retrieval": retrieval_summary,
        "failures": failures,
        "cases": {"classification": classification_rows, "retrieval": retrieval_rows},
    }


def write_markdown_report(results: dict[str, object], path: Path = DEFAULT_REPORT_PATH) -> None:
    classification = results["classification_and_grounding"]
    retrieval = results["retrieval"]
    failures = results["failures"]
    lines = [
        "# Evaluation Report",
        "",
        "Generated from the checked-in classification and retrieval evaluation sets.",
        "",
        "## Release targets",
        "",
        f"- Claim-level faithfulness: **{classification['claim_level_faithfulness']:.1%}** (target ≥95%).",
        f"- Retrieval Recall@5: **{retrieval['recall_at_5']:.1%}**.",
        f"- Retrieval MRR: **{retrieval['mrr']:.3f}**; nDCG@5: **{retrieval['ndcg_at_5']:.3f}**.",
        f"- Refusal accuracy: **{retrieval['refusal_accuracy']:.1%}**.",
        f"- p50/p95 latency: **{classification['latency_p50_seconds']:.3f}s / {classification['latency_p95_seconds']:.3f}s** (p95 target ≤5s).",
        "",
        "## Classification and citation checks",
        "",
        f"- Software-category accuracy: {classification['software_category_accuracy']:.1%}.",
        f"- U.S.-status accuracy: {classification['us_status_accuracy']:.1%}.",
        f"- Required-source recall: {classification['required_source_recall']:.1%}.",
        f"- Citation metadata validity: {classification['citation_metadata_validity']:.1%}.",
        f"- Inline citation validity: {classification['inline_citation_validity']:.1%}.",
        "",
        "## Failure analysis",
        "",
    ]
    if failures:
        lines.extend(f"- `{row['id']}`: {', '.join(row['failed_checks'])}." for row in failures)
    else:
        lines.append("- No automated release-check failures in the current development sets.")
    lines.extend(
        [
            "- The sets are small, curated development benchmarks and are not proof of real-world regulatory correctness.",
            "- Metadata-constrained supplemental retrieval makes controlling source-family recall robust, but may hide ranking weakness in a larger heterogeneous corpus.",
            "- The offline hashing embedding is a reproducible baseline; semantic paraphrases and domain drift remain material risks.",
            "- IEC and ISO records are catalog-level summaries. Licensed clause text is intentionally absent, so clause-level questions must be refused or escalated.",
            "- Regulatory classification still depends on complete claims, architecture, hazards, and jurisdiction-specific professional review.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    args = parser.parse_args()
    results = evaluate()
    write_markdown_report(results, args.report)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
