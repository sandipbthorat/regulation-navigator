# Medical Device Software Regulatory Navigator

A runnable LangChain/LangGraph MVP that screens one medical-software function,
retrieves source-linked regulatory evidence, validates citation lifecycle metadata,
and returns a structured preliminary assessment.

**My RAG app helps medical-device regulatory, quality, and software professionals answer software-classification and applicable-requirement questions from 21 curated, English-language FDA, U.S. statutory, EU MDR, IMDRF, IEC, and ISO evidence cards in a Streamlit application with ≥95% claim-level faithfulness and p95 latency ≤5 seconds.**

The application is designed for medical-device quality, regulatory, and software
professionals. The current development benchmark measures **100% claim-level
faithfulness** and **0.005-second p95 assessment latency**; the declared release
targets are at least 95% and at most 5 seconds. These results describe the checked-in
35-case development sets, not independent validation or real-world legal accuracy.

> This is an educational research tool, not legal advice, an FDA/EU decision, or a
> conformity assessment. Classification depends on exact claims, architecture,
> users, hazards, risk controls, and the current law in each market.

## What the MVP does

- Uses a typed LangGraph state and explicit decision nodes instead of delegating
  regulatory applicability to a free-form chatbot.
- Screens Device Software Function, SaMD, embedded/integral software, CDS,
  data-only/MDDS, general wellness, accessory, AI/ML, cybersecurity, OTS, and
  non-product/manufacturing contexts.
- Produces preliminary FDA device status, IMDRF SaMD category, IEC 62304 safety
  class, and EU MDR Rule 11 result while preserving unresolved facts.
- Uses BM25 + a local Chroma vector index with reciprocal-rank fusion. Exact source
  identifiers receive an additional retrieval boost.
- Rejects superseded or incomplete citations and reports source-family coverage.
- Binds each displayed classification claim to its required source family and blocks
  release when claim coverage falls below 80%, the corpus is stale, or the request is
  outside the indexed scope.
- Runs without an API key. Optional structured LLM fact extraction is gated behind
  `REGNAV_USE_LLM=true`; deterministic rules still control classification.

## Architecture

```mermaid
flowchart TD
    A[Software function description + known facts] --> B[Structured fact extraction]
    B --> C[Software scope classification]
    C --> D{CDS function?}
    D -->|Yes| E[Section 520(o) CDS screen]
    D -->|No| F[General U.S. device screen]
    E --> G[IMDRF SaMD matrix]
    F --> G
    G --> H[IEC 62304 safety-class screen]
    H --> I[EU MDR Rule 11 screen]
    I --> J[Applicability and missing-fact questions]
    J --> K[BM25 + Chroma hybrid retrieval]
    K --> L[Citation status and coverage validation]
    L --> M[Atomic claim grounding and release gate]
    M --> N[Structured cited assessment]
```

The graph intentionally asks for missing inputs instead of converting uncertainty
into a confident classification. LangChain components handle document objects,
embeddings, BM25 retrieval, and Chroma; LangGraph controls the regulatory workflow.

The complete handout framework, prompt inventory, iterations, observations, and
submission checklist are in [`docs/PROJECT_SUBMISSION.md`](docs/PROJECT_SUBMISSION.md).

## Quick start

Python 3.12 is recommended.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
cp .env.example .env
streamlit run app.py
```

The first assessment creates a local Chroma collection under `.cache/chroma`.
No source text or query leaves the machine unless optional LLM extraction or
LangSmith tracing is explicitly enabled.

Run the command-line interface:

```bash
regnav assess \
  --description "Standalone ML software that detects stroke from CT images for a radiologist" \
  --medical-purpose yes \
  --standalone yes \
  --ai-ml yes \
  --analyzes-medical-image-or-signal yes \
  --intended-user clinician \
  --information-significance treat_or_diagnose \
  --condition-severity critical \
  --hazard-severity death_or_serious_injury
```

To inspect the graph in LangGraph's local development environment:

```bash
python -m pip install -U "langgraph-cli[inmem]"
langgraph dev
```

## Optional LLM extraction

The default path is local and deterministic. To let an OpenAI model extract
candidate facts from natural language, set:

```dotenv
OPENAI_API_KEY=...
REGNAV_MODEL=gpt-5-mini
REGNAV_USE_LLM=true
```

The LLM returns a constrained schema. Explicit user fields override model output,
and the regulatory classifications remain deterministic. If the model call fails,
the graph falls back to local extraction.

## Corpus and ingestion

The bundled [`starter_corpus.jsonl`](data/corpus/starter_corpus.jsonl) contains
compact evidence cards linked to official/public source pages. It is a demo index,
not a substitute for reading the source documents.

Ingest an organization-authorized PDF, Markdown, or text source:

```bash
regnav ingest ./authorized_sources/cds-guidance.pdf \
  --output data/processed/authorized.jsonl \
  --jurisdiction US \
  --authority FDA \
  --document-type "Final guidance" \
  --status Final \
  --date 2026-01-29 \
  --source-url "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software" \
  --source-key fda_cds
```

Then set `REGNAV_CORPUS_PATH=data/processed/authorized.jsonl` and restart the app.
The ingester preserves Markdown heading paths and PDF page numbers before creating
1,600-character chunks with 200-character overlap. This size keeps one regulatory
provision or evidence-card concept intact while retaining enough boundary context;
the default 384-dimensional signed hashing embedding is offline and reproducible,
and is combined with BM25 because exact identifiers such as “Rule 11” and “520(o)”
matter alongside semantic similarity.

Official issuing authorities own the source-of-truth documents; the project
maintainer owns the indexed snapshots and review log. Every source family is reviewed
monthly under a 30-day freshness SLA, with a one-business-day update target for a
known repeal, supersession, safety alert, or material enforcement change. Run
`regnav audit-corpus` to enforce that policy.

IEC and ISO standards are copyrighted. The starter corpus includes only scope-level
summaries and catalog links. Add clause text only when your organization's license
permits ingestion, storage, and downstream use.

## Evaluation

Run unit and integration tests:

```bash
pytest
```

Run the starter gold-set evaluation:

```bash
python -m regulation_navigator.evaluate
```

The evaluator covers 20 end-to-end classification cases and 15 retrieval/refusal
cases. It reports claim-level faithfulness, inline-citation validity, source recall,
Recall@5, MRR, nDCG@5, refusal accuracy, and p50/p95 latency, and writes
[`docs/EVALUATION_REPORT.md`](docs/EVALUATION_REPORT.md) with explicit failure
analysis. The sets remain development aids and should be independently reviewed and
expanded before production use.

## Project structure

```text
.
├── app.py                         # Streamlit UI
├── data/
│   ├── corpus/                    # Source-linked starter evidence cards
│   └── evals/                     # Gold test cases
├── src/regulation_navigator/
│   ├── graph.py                   # Compiled LangGraph workflow
│   ├── models.py                  # Typed input and graph state
│   ├── rules.py                   # Deterministic decision nodes
│   ├── retrieval.py               # BM25 + Chroma hybrid RAG
│   ├── citations.py               # Currency/metadata/coverage checks
│   ├── ingest.py                  # Hierarchical ingestion
│   ├── prompts.py                 # Constrained optional-LLM prompts
│   ├── grounding.py               # Atomic claims, inline citations, refusal gate
│   ├── freshness.py               # Source-review cadence and freshness SLA
│   └── render.py                  # UI-neutral result contract
└── tests/
```

## Submission artifacts

- Google Docs-ready project report: [`output/docx/Regulation_Navigator_Week_2_Submission.docx`](output/docx/Regulation_Navigator_Week_2_Submission.docx)
- Narrated 3:49 walkthrough: [`output/video/Regulation_Navigator_Demo.mp4`](output/video/Regulation_Navigator_Demo.mp4)
- Walkthrough transcript: [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md)
- Evaluation report: [`docs/EVALUATION_REPORT.md`](docs/EVALUATION_REPORT.md)
- Full handout response: [`docs/PROJECT_SUBMISSION.md`](docs/PROJECT_SUBMISSION.md)

The repository is ready to publish, but this environment has no GitHub CLI and no
configured remote. Add the chosen GitHub repository as `origin` and push `main`, or
upload the generated ZIP submission package through GitHub’s web interface.

## Deliberate limitations

- This MVP performs **qualification and framework screening**, not final U.S.
  product-code/class/pathway determination or EU conformity assessment.
- Rule 11 and IEC 62304 classes are preliminary. Full architecture, hazard analysis,
  risk controls, target population, and clinical workflow are required.
- FDA guidance expresses current agency thinking and is generally nonbinding unless
  a binding requirement is separately cited.
- IMDRF categories are harmonized relative-impact categories, not FDA classes or EU
  MDR classes.
- The offline hashing embedding is a transparent baseline. Replace it with an
  evaluated embedding model and reranker before production use.
- Source currency must be monitored. The `date`, `status`, and `superseded` fields
  exist to make that maintenance testable.
