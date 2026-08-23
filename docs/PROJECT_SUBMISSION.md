# Week 2 Project Submission — Regulation Navigator

## One-line RAG application statement

My RAG app helps medical-device regulatory, quality, and software professionals answer software-classification and applicable-requirement questions from 21 curated, English-language FDA, U.S. statutory, EU MDR, IMDRF, IEC, and ISO evidence cards in a Streamlit application with ≥95% claim-level faithfulness and p95 latency ≤5 seconds.

## Project overview

The Medical Device Software Regulatory Navigator screens one software function at a time and produces a preliminary, cited view of software type, U.S. FDA device status, Non-Device CDS eligibility, IMDRF SaMD category, IEC 62304 safety class, EU MDR Rule 11 class, and applicable lifecycle frameworks. A typed LangGraph workflow separates deterministic regulatory decision logic from retrieval, citation validation, claim grounding, refusal behavior, and presentation.

The intended users are medical-device regulatory, quality, and software professionals performing early product-definition or change-impact triage. The application is educational research support—not legal advice, an agency determination, or a conformity assessment—and it preserves missing facts as follow-up questions.

## Required framework

### Use case

The app answers preliminary software-qualification, classification, and applicable-framework questions for a single described medical-software function. It returns cited claims, caveats, unresolved facts, and official source links in a Streamlit interface rather than a free-form legal conclusion.

### Corpus

The corpus contains 21 curated English-language JSONL evidence cards covering FDA guidance and regulations, U.S. statutes, EU MDR, IMDRF SaMD documents, IEC 62304, and ISO 14971; ingestion also accepts authorized PDF, Markdown, and plain-text files. Official issuing authorities own the source-of-truth documents, while the project maintainer owns the indexed snapshots, metadata, and review log.

### Ingestion and cleaning

The ingestion CLI extracts PDF pages, Markdown heading paths, or text documents; normalizes whitespace; splits at semantic boundaries when possible; and attaches jurisdiction, authority, document type, legal status, date, section, URL, source family, supersession, and review metadata. Duplicate chunk identifiers are deterministically replaced during corpus loading, and empty or metadata-incomplete records fail validation.

### Ingestion and freshness

Every active source family is reviewed monthly under a 30-day freshness SLA; a known repeal, supersession, safety alert, or material enforcement change has a one-business-day update target. `regnav audit-corpus` compares the review manifest with every active corpus source family, and the answer release gate refuses a grounded assessment when the audit is stale or incomplete.

### Chunking and embedding

Authorized documents are split hierarchically into approximately 1,600-character chunks with 200-character overlap, preserving Markdown headings or PDF page numbers; this is large enough to keep one provision or coherent regulatory concept together while retaining boundary context. The MVP uses a reproducible 384-dimensional signed feature-hashing embedding so it runs offline, paired with BM25 because exact terms such as “Rule 11,” “N12,” “IEC 62304,” and “520(o)” are decision-critical; a production system should benchmark a domain embedding and reranker.

### Retrieve

Evidence is stored in local Chroma and a parallel BM25 index, then retrieved with 56% lexical and 44% vector reciprocal-rank fusion plus exact-identifier boosts. Default top-k is 8; metadata-constrained supplemental retrieval guarantees that each decision-critical source family is represented before citations and lifecycle status are validated.

## Data and source lifecycle

Each evidence card includes a stable chunk ID, source-family key, jurisdiction, authority, document, document type, current/draft/licensed status, issue date, section, official URL, supersession flag, topic tags, and a concise non-infringing evidence summary. The index distinguishes binding statutes and regulations from nonbinding final guidance, draft guidance, voluntary harmonized frameworks, and licensed consensus standards.

IEC and ISO clause text is intentionally not reproduced. The app provides scope-level catalog evidence and tells users to consult a licensed copy for clause-level conclusions.

## Application and graph design

The LangGraph flow is:

1. Validate the typed input and extract only supported facts; explicit fields override optional model extraction.
2. Classify software scope and route CDS versus general U.S. analysis.
3. Screen U.S. status, IMDRF N10/N12, IEC 62304, and EU MDR Rule 11 with deterministic nodes.
4. Collect unresolved facts and determine applicable source families.
5. Run hybrid BM25/Chroma retrieval and validate source URL, section, status, and supersession metadata.
6. Convert displayed conclusions into atomic claims, attach required source-family citations, audit freshness, and apply answer/refusal gates.
7. Render a structured cited assessment, evidence table, quality metrics, warning labels, and official links.

The default application works without an API key. Optional OpenAI structured extraction can turn natural-language descriptions into candidate facts, but it cannot decide regulatory applicability and automatically falls back to the deterministic path if unavailable.

## Prompts and agent instructions

### Fact extraction system instruction

Extract only facts about one medical-software function that the description actually supports. Use null or “unknown” for missing facts and do not infer clinical severity, hardware independence, or whether an HCP can independently review a recommendation.

### Fact extraction user prompt

Provide the software description and intended-use statement, then request the constrained `AssessmentInput` fact schema. Explicit user-entered form facts remain authoritative over extracted candidates.

### Grounded assessment instruction

Use only deterministic classifications and supplied evidence; label every conclusion preliminary; cite evidence with `[chunk_id]`; distinguish law, final guidance, draft guidance, and harmonized frameworks; never reconstruct licensed IEC/ISO text; and preserve missing facts. The current offline path implements this instruction deterministically by binding each atomic claim to required source keys, which makes citation validation testable without an LLM judge.

## Refusal and uncertainty behavior

The app refuses unrelated or explicitly unsupported topics such as recipes, HIPAA, billing, and reimbursement because they are outside the corpus. It also refuses release when claim-level source coverage is below 80% or the freshness manifest fails; otherwise it returns “answer with caveats” when material facts remain unresolved and displays specific follow-up questions.

The 80% operational release gate prevents a partially grounded multi-framework answer. The higher project success target—at least 95% mean claim-level faithfulness—governs evaluation and release review.

## Evaluation results

The checked-in development benchmark contains 20 end-to-end classification cases and 15 retrieval/refusal cases. On the 2026-08-22 local run:

- Software-category accuracy: 100%.
- U.S.-status accuracy: 100%.
- Required-source recall: 100%.
- Claim-level faithfulness and inline-citation validity: 100%.
- Retrieval Recall@5: 100%; MRR: 0.933; nDCG@5: 0.951.
- Refusal accuracy: 100%.
- Assessment latency: 0.004 seconds p50 and 0.005 seconds p95, below the 5-second target. The first cold index load was approximately 0.257 seconds.

These are curated development results, not independent validation. They show that the software contract is measurable and currently passes its release gates; they do not establish legal correctness on unseen products.

## Iterations tried

### Iteration 1 — rule-only structured result

The first version used deterministic rules and returned classifications plus a list of evidence records. It was reproducible, but the prose rationale was not explicitly bound claim-by-claim to citations, and the evaluation measured only broad source recall.

### Iteration 2 — semantic retrieval baseline

A local Chroma index with feature-hashing embeddings enabled offline semantic retrieval. Tests showed that exact regulatory identifiers could be displaced by semantically related evidence, particularly when the query mixed several frameworks.

### Iteration 3 — hybrid retrieval and source-family supplements

BM25, vector ranking, reciprocal-rank fusion, and exact-identifier boosts improved direct queries. Metadata-constrained supplements then ensured that every framework selected by the decision graph had at least one controlling source, while ranking metrics remained separately measurable on raw retrieval queries.

### Iteration 4 — claim grounding, freshness, and refusal gates

Each displayed classification became an atomic claim with required source keys and validated inline citation IDs. A source review manifest, stale-index block, out-of-corpus refusal, latency instrumentation, and claim-level evaluation closed the remaining handout criteria.

## Learnings and observations

- Regulatory RAG needs both semantic matching and exact retrieval because citation identifiers and framework names often carry more meaning than surrounding prose.
- Deterministic decision nodes make ambiguous facts visible and testable; an LLM is more useful for constrained fact extraction and prose than for deciding legal applicability.
- High source recall alone is not faithfulness. The output must bind each material claim to the evidence family that supports that claim and reject invented citation IDs.
- Publication date and index-review date solve different problems. A 2019 standard can still be the current edition, while a recently published source can still be missing from a stale index.
- Supplemental source-family retrieval protects completeness but can conceal weak ranking, so raw Recall@k, MRR, and nDCG must be evaluated separately.
- Small curated benchmarks can look perfect. Production readiness requires blind expert review, adversarial descriptions, a larger licensed corpus, drift monitoring, and jurisdiction-specific pathway validation.

## AI coding tools used

Codex was used to scaffold and implement the Python project, inspect the handout, refine the LangGraph workflow, add automated evaluation, run tests and static checks, and generate the submission artifacts. Human review remains required for regulatory interpretations, source licensing, benchmark labels, and final submission decisions.

## Reproduction

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
streamlit run app.py
pytest
python -m regulation_navigator.evaluate
regnav audit-corpus
```

## Deliverable checklist

- Runnable Streamlit RAG application: complete.
- LangChain/LangGraph retrieval and orchestration: complete.
- Source-linked corpus and ingestion path: complete.
- Faithfulness, relevance, refusal, freshness, and latency evaluation: complete.
- Project overview, datasets, prompts, iterations, and learnings: complete in this document.
- Google Docs-ready `.docx`: generated from this content and visually verified as a separate artifact.
- Demo script and ≤5-minute video artifact: included in the submission package.
- Public GitHub repository: https://github.com/sandipbthorat/regulation-navigator
- Public application: https://medical-regulation-navigator.streamlit.app

## Limitations and required human review

This tool does not determine U.S. product code, FDA class, submission pathway, EU conformity route, clinical evidence sufficiency, or final IEC 62304 class. Exact intended use, architecture, users, failure consequences, risk controls, current source text, and qualified regulatory review remain necessary.
