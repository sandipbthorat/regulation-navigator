# Regulation Navigator — Submission Package

This package contains the complete Week 2 Regulation Navigator project, its source-linked corpus, evaluation assets, Google Docs-ready report, and narrated demonstration.

## Published project

- Live application: https://medical-regulation-navigator.streamlit.app
- Public repository: https://github.com/sandipbthorat/regulation-navigator
- Deployment source: `main` branch, `app.py`

## Start here

- Project overview and setup: `README.md`
- Google Docs-ready report: `output/docx/Regulation_Navigator_Week_2_Submission.docx`
- Narrated 3:49 walkthrough: `output/video/Regulation_Navigator_Demo.mp4`
- Full handout response: `docs/PROJECT_SUBMISSION.md`
- Evaluation report: `docs/EVALUATION_REPORT.md`
- Demo transcript: `docs/DEMO_SCRIPT.md`

## Release verification

- 11 automated tests passed.
- Ruff formatting and lint checks passed.
- Claim-level faithfulness: 100%.
- Retrieval Recall@5: 100%; MRR: 0.933; nDCG@5: 0.951.
- Refusal accuracy: 100%.
- Assessment latency: 0.006 seconds p50 and 0.008 seconds p95 against a 5-second target.
- The seven-page report passed Google Docs title sanitization and full rendered-page visual inspection.
- The deployed Streamlit application completed an end-to-end cited assessment.

## Key-file SHA-256 checksums

```text
ba17a58d072a878a22d9a45540379610c2232102236f77fa3d84729bbd2e8cd7  output/docx/Regulation_Navigator_Week_2_Submission.docx
269f7023d887b671fe2f43736dd0c803a1bc89e337d42238073d2f963d17c03d  output/video/Regulation_Navigator_Demo.mp4
```

The package excludes virtual environments, caches, build directories, secrets, temporary Word lock files, and other local-only artifacts. The application runs in deterministic mode without an API key.
