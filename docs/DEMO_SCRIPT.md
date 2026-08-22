# Regulation Navigator — Demo Script

Target length: approximately 3 minutes 30 seconds; hard submission limit: 5 minutes.

## 0:00–0:25 — Project and user

Medical Device Software Regulatory Navigator is a RAG application for regulatory, quality, and software professionals who need an early, source-grounded screen of one software function. It covers U.S. FDA software policy, EU MDR Rule 11, IMDRF SaMD, IEC 62304, and ISO 14971. Every result is preliminary and keeps legal and conformity decisions with qualified reviewers.

## 0:25–0:52 — Input and corpus

The Streamlit surface begins with a single-function description and typed facts. The bundled knowledge corpus has 21 curated English evidence cards linked to official FDA, U.S. statutory, EU, IMDRF, IEC, and ISO pages. Authorized PDFs, Markdown, and text can be added through the ingestion CLI. Missing facts stay unknown instead of being silently guessed.

## 0:52–1:20 — Live example and graph

For the walkthrough, the software runs on a surgical robotic platform, analyzes sensor information, and alerts a surgeon. I identify it as medical-purpose software that is part of hardware, uses a clinician, analyzes a signal, and could contribute to death or serious injury. LangGraph routes the case through scope, CDS, U.S., IMDRF, IEC, EU, retrieval, citation, freshness, and release-gate nodes.

## 1:20–1:52 — Final result

The live result classifies the function as software in a medical device and a likely FDA device software function. It is not SaMD under IMDRF N10 because it is part of hardware. The preliminary IEC 62304 screen is Class C, and EU classification requires the implementing-rule and driven-device analysis. Each displayed conclusion is an atomic claim with inline source IDs, and the disclaimer remains visible.

## 1:52–2:18 — Retrieval and sources

Retrieval combines BM25 and local Chroma embeddings with reciprocal-rank fusion and exact-identifier boosts. Default top-k is eight. Metadata-constrained supplements ensure every decision-critical source family is present, while raw retrieval quality is evaluated separately. The source table distinguishes statutes, binding regulations, final guidance, draft guidance, international frameworks, and licensed standards.

## 2:18–2:44 — Quality gates

The quality tab makes the evidence contract visible. This run has ten validated citations, one hundred percent applicability-source coverage, one hundred percent claim-level faithfulness, and a current source review under the thirty-day freshness SLA. The app refuses out-of-corpus requests, stale evidence, or severely incomplete citation coverage, and warns that IEC and ISO clause-level work requires licensed standards.

## 2:44–3:05 — Evidence detail

Each evidence card shows a stable citation ID, document, section, authority, status, date, concise supporting text, and an official source link. The IEC card deliberately provides only scope-level evidence and directs the user to a licensed copy. That boundary prevents the RAG system from reconstructing copyrighted standard text or overstating a catalog summary.

## 3:05–3:38 — Evaluation, coding tools, and handoff

The checked-in evaluation includes 20 classification cases and 15 retrieval and refusal cases. The current development run measured 100 percent claim-level faithfulness, 100 percent Recall at five, 0.951 nDCG at five, and 0.005-second p95 assessment latency. Codex helped scaffold the project, inspect the handout, refine the LangGraph workflow, run tests, and generate submission artifacts. The repository includes the app, corpus, tests, evaluation report, Google Docs-ready project document, and this under-five-minute walkthrough.

