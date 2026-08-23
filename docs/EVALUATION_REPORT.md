# Evaluation Report

Generated from the checked-in classification and retrieval evaluation sets.

## Release targets

- Claim-level faithfulness: **100.0%** (target ≥95%).
- Retrieval Recall@5: **100.0%**.
- Retrieval MRR: **0.933**; nDCG@5: **0.951**.
- Refusal accuracy: **100.0%**.
- p50/p95 latency: **0.006s / 0.008s** (p95 target ≤5s).

## Classification and citation checks

- Software-category accuracy: 100.0%.
- U.S.-status accuracy: 100.0%.
- Required-source recall: 100.0%.
- Citation metadata validity: 100.0%.
- Inline citation validity: 100.0%.

## Failure analysis

- No automated release-check failures in the current development sets.
- The sets are small, curated development benchmarks and are not proof of real-world regulatory correctness.
- Metadata-constrained supplemental retrieval makes controlling source-family recall robust, but may hide ranking weakness in a larger heterogeneous corpus.
- The offline hashing embedding is a reproducible baseline; semantic paraphrases and domain drift remain material risks.
- IEC and ISO records are catalog-level summaries. Licensed clause text is intentionally absent, so clause-level questions must be refused or escalated.
- Regulatory classification still depends on complete claims, architecture, hazards, and jurisdiction-specific professional review.
