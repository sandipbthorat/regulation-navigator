"""Hierarchical document ingestion for organization-authorized source files."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", flags=re.MULTILINE)


@dataclass(frozen=True)
class SourceMetadata:
    jurisdiction: str
    authority: str
    document_type: str
    status: str
    date: str
    source_url: str
    source_key: str
    superseded: bool = False


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized[:72] or "source"


def _window(text: str, chunk_size: int = 1_600, overlap: int = 200) -> list[str]:
    text = re.sub(r"[ \t]+", " ", text).strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        if end < len(text):
            boundary = max(text.rfind("\n", start, end), text.rfind(". ", start, end))
            if boundary > start + chunk_size // 2:
                end = boundary + 1
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks


def _markdown_sections(text: str) -> list[tuple[str, str]]:
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        return [("Document", text)]
    sections: list[tuple[str, str]] = []
    if matches[0].start() > 0 and text[: matches[0].start()].strip():
        sections.append(("Preamble", text[: matches[0].start()]))
    hierarchy: list[str] = []
    for index, match in enumerate(matches):
        level = len(match.group(1))
        heading = match.group(2).strip()
        hierarchy = hierarchy[: level - 1]
        hierarchy.append(heading)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end() : end].strip()
        if body:
            sections.append((" > ".join(hierarchy), body))
    return sections


def _read_sections(path: Path) -> list[tuple[str, str]]:
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown"}:
        return _markdown_sections(path.read_text(encoding="utf-8"))
    if suffix == ".txt":
        return [("Document", path.read_text(encoding="utf-8"))]
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("PDF ingestion requires pypdf. Run `pip install -e .`.") from exc
        reader = PdfReader(str(path))
        return [
            (f"Page {page_number}", page.extract_text() or "")
            for page_number, page in enumerate(reader.pages, 1)
        ]
    raise ValueError(f"Unsupported source type: {path.suffix}")


def iter_source_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return
    for source in sorted(path.rglob("*")):
        if source.is_file() and source.suffix.lower() in {".md", ".markdown", ".txt", ".pdf"}:
            yield source


def ingest_path(path: Path, metadata: SourceMetadata) -> list[dict]:
    records: list[dict] = []
    for source in iter_source_files(path):
        for section, text in _read_sections(source):
            for chunk_index, chunk in enumerate(_window(text), 1):
                digest = hashlib.sha256(
                    f"{source.resolve()}|{section}|{chunk_index}|{chunk}".encode()
                ).hexdigest()[:12]
                records.append(
                    {
                        "chunk_id": f"{_slug(source.stem)}-{digest}",
                        "source_key": metadata.source_key,
                        "jurisdiction": metadata.jurisdiction,
                        "authority": metadata.authority,
                        "document": source.stem,
                        "document_type": metadata.document_type,
                        "status": metadata.status,
                        "date": metadata.date,
                        "section": section,
                        "source_url": metadata.source_url,
                        "superseded": metadata.superseded,
                        "reviewed_at": datetime.now(UTC).date().isoformat(),
                        "local_source": source.name,
                        "text": chunk,
                    }
                )
    return records


def write_jsonl(records: list[dict], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
