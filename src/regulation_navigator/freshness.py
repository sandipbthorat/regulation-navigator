"""Corpus review-cadence and freshness-SLA checks."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from regulation_navigator.config import PROJECT_ROOT
from regulation_navigator.corpus import load_corpus

FRESHNESS_MANIFEST = PROJECT_ROOT / "data" / "corpus" / "freshness_manifest.json"


def load_freshness_manifest(path: Path = FRESHNESS_MANIFEST) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def audit_corpus_freshness(
    *,
    as_of: date | None = None,
    manifest_path: Path = FRESHNESS_MANIFEST,
    corpus_paths: list[Path | None] | None = None,
) -> dict[str, Any]:
    """Validate that every active source family has a current review record."""

    manifest = load_freshness_manifest(manifest_path)
    review_date = date.fromisoformat(manifest["reviewed_at"])
    today = as_of or datetime.now(UTC).date()
    sla_days = int(manifest["freshness_sla_days"])
    age_days = (today - review_date).days

    if corpus_paths is None:
        corpus_paths = [PROJECT_ROOT / "data" / "corpus" / "starter_corpus.jsonl"]
    records = load_corpus(corpus_paths)
    active_keys = {record["source_key"] for record in records if not record["superseded"]}
    reviewed_keys = set(manifest.get("reviewed_source_keys", []))
    missing_keys = sorted(active_keys.difference(reviewed_keys))
    unknown_keys = sorted(reviewed_keys.difference(active_keys))
    current = age_days <= sla_days and not missing_keys and not unknown_keys
    return {
        "status": "current" if current else "stale_or_incomplete",
        "reviewed_at": review_date.isoformat(),
        "as_of": today.isoformat(),
        "age_days": age_days,
        "freshness_sla_days": sla_days,
        "review_cadence": manifest["review_cadence"],
        "critical_update_sla": manifest["critical_update_sla"],
        "source_family_count": len(active_keys),
        "missing_source_keys": missing_keys,
        "unknown_source_keys": unknown_keys,
    }
