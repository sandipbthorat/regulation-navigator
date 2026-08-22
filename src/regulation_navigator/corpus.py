"""Corpus loading and conversion to LangChain documents."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

REQUIRED_METADATA = {
    "chunk_id",
    "source_key",
    "jurisdiction",
    "authority",
    "document",
    "document_type",
    "status",
    "date",
    "section",
    "source_url",
    "superseded",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            record = json.loads(line)
            missing = REQUIRED_METADATA.difference(record)
            if missing:
                missing_text = ", ".join(sorted(missing))
                raise ValueError(f"{path}:{line_number} missing metadata: {missing_text}")
            if not record.get("text", "").strip():
                raise ValueError(f"{path}:{line_number} has no text")
            records.append(record)
    return records


def load_corpus(paths: Iterable[Path | None]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for path in paths:
        if path is None:
            continue
        if not path.exists():
            raise FileNotFoundError(f"Corpus file does not exist: {path}")
        for record in load_jsonl(path):
            by_id[record["chunk_id"]] = record
    return list(by_id.values())


def to_documents(records: list[dict[str, Any]]):
    """Convert validated records to ``langchain_core.documents.Document`` objects."""

    try:
        from langchain_core.documents import Document
    except ImportError as exc:  # pragma: no cover - exercised by setup failures
        raise RuntimeError("LangChain is not installed. Run `pip install -e .` first.") from exc

    documents = []
    for record in records:
        metadata = {key: value for key, value in record.items() if key != "text"}
        # Chroma accepts scalar metadata, not lists.
        if isinstance(metadata.get("topics"), list):
            metadata["topics"] = " | ".join(metadata["topics"])
        documents.append(Document(page_content=record["text"], metadata=metadata))
    return documents
