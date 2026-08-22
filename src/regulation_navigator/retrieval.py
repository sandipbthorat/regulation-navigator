"""Hybrid BM25 + Chroma retrieval with reciprocal-rank fusion."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from functools import lru_cache
from typing import Any

from rank_bm25 import BM25Okapi

from regulation_navigator.config import Settings
from regulation_navigator.corpus import load_corpus, to_documents
from regulation_navigator.embeddings import HashingEmbeddings

SOURCE_QUERIES = {
    "fda_device_definition": "FD&C Act section 201(h) device definition intended medical purpose",
    "fdca_520o": "FD&C Act section 520(o) software functions excluded device definition",
    "fda_device_software_policy": "FDA policy device software functions platform function specific",
    "fda_cds": "FDA Clinical Decision Support section 520(o)(1)(E) HCP independent review",
    "fda_general_wellness": "FDA general wellness low risk healthy lifestyle guidance",
    "fda_mdds": "FDA MDDS only transfer store convert format display device data",
    "fda_premarket_software": "FDA content premarket submissions device software documentation",
    "fda_ots": "FDA off-the-shelf OTS software medical device hazard anomalies",
    "fda_cybersecurity": "FDA cybersecurity medical device secure product development QMSR",
    "fda_ai_lifecycle": "FDA AI-enabled device software lifecycle draft guidance",
    "fda_ai_pccp": "FDA predetermined change control plan AI device software PCCP",
    "fda_qmsr": "21 CFR Part 820 QMSR quality management system software validation",
    "iec_62304": "IEC 62304 medical device software lifecycle safety class A B C",
    "iso_14971": "ISO 14971 medical device risk management hazards risk control",
    "imdrf_n10": "IMDRF N10 SaMD key definition independent hardware",
    "imdrf_n12": "IMDRF N12 SaMD risk category matrix I II III IV",
    "imdrf_n23": "IMDRF N23 SaMD quality management system",
    "imdrf_n41": "IMDRF N41 SaMD clinical evaluation validation",
    "eu_mdr_rule11": "EU MDR 2017/745 Annex VIII Rule 11 medical device software class",
}

BM25_TOKEN_RE = re.compile(r"[a-z0-9]+(?:\([a-z0-9]+\))*", re.IGNORECASE)


def _bm25_tokens(text: str) -> list[str]:
    return BM25_TOKEN_RE.findall(text.lower())


class BM25Index:
    """Small direct BM25 index over LangChain documents."""

    def __init__(self, documents: list[Any]) -> None:
        self.documents = documents
        self.index = BM25Okapi([_bm25_tokens(document.page_content) for document in documents])

    def search(self, query: str, k: int) -> list[Any]:
        scores = self.index.get_scores(_bm25_tokens(query))
        ranked = sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)
        return [self.documents[index] for index in ranked[:k]]


def _record_from_document(document, score: float) -> dict[str, Any]:
    record = dict(document.metadata)
    record["text"] = document.page_content
    record["score"] = round(score, 6)
    return record


class HybridRegulatoryRetriever:
    """Fuse lexical and vector ranks, then apply lifecycle metadata gates."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.records = load_corpus([self.settings.starter_corpus, self.settings.additional_corpus])
        self.documents = to_documents(self.records)
        self._by_id = {record["chunk_id"]: record for record in self.records}
        self._build_indexes()

    def _build_indexes(self) -> None:
        try:
            from langchain_chroma import Chroma
        except ImportError as exc:  # pragma: no cover - setup failure
            raise RuntimeError(
                "Retrieval dependencies are missing. Run `pip install -e .`."
            ) from exc

        self.bm25 = BM25Index(self.documents)
        self.bm25_k = min(len(self.documents), max(self.settings.top_k * 3, 12))

        fingerprint_source = json.dumps(self.records, sort_keys=True, ensure_ascii=False)
        fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()[:12]
        collection_name = f"regnav_{fingerprint}"
        self.settings.chroma_dir.mkdir(parents=True, exist_ok=True)
        self.vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=HashingEmbeddings(),
            persist_directory=str(self.settings.chroma_dir),
            collection_metadata={"hnsw:space": "cosine"},
        )
        existing = set(self.vectorstore.get(include=[]).get("ids", []))
        missing_documents = [
            doc for doc in self.documents if doc.metadata["chunk_id"] not in existing
        ]
        if missing_documents:
            self.vectorstore.add_documents(
                missing_documents,
                ids=[doc.metadata["chunk_id"] for doc in missing_documents],
            )

    @staticmethod
    def _exact_tokens(query: str) -> set[str]:
        patterns = [
            r"\b\d+\s*CFR\s*(?:Part\s*)?\d+\b",
            r"\bRule\s*\d+\b",
            r"\bIEC\s*\d+\b",
            r"\bISO\s*\d+\b",
            r"\bN\d+\b",
            r"\b\d+\(o\)(?:\(\d+\))?(?:\([A-Z]\))?\b",
        ]
        return {
            match.group(0).lower().replace(" ", "")
            for pattern in patterns
            for match in re.finditer(pattern, query, flags=re.IGNORECASE)
        }

    def search(self, query: str, k: int | None = None) -> list[dict[str, Any]]:
        k = k or self.settings.top_k
        lexical = self.bm25.search(query, self.bm25_k)
        vector = self.vectorstore.similarity_search(query, k=min(len(self.documents), k * 3))
        scores: dict[str, float] = defaultdict(float)
        documents: dict[str, Any] = {}

        for weight, ranked in ((0.56, lexical), (0.44, vector)):
            for rank, document in enumerate(ranked, 1):
                chunk_id = document.metadata["chunk_id"]
                documents[chunk_id] = document
                scores[chunk_id] += weight / (40 + rank)

        exact = self._exact_tokens(query)
        for chunk_id, document in documents.items():
            haystack = (
                f"{document.metadata.get('section', '')} {document.page_content}".lower().replace(
                    " ", ""
                )
            )
            scores[chunk_id] += 0.02 * sum(token in haystack for token in exact)

        ranked_ids = sorted(scores, key=scores.get, reverse=True)
        return [
            _record_from_document(documents[chunk_id], scores[chunk_id])
            for chunk_id in ranked_ids
            if not documents[chunk_id].metadata.get("superseded", False)
        ][:k]

    def retrieve_for_assessment(
        self,
        description: str,
        source_keys: list[str],
        k: int | None = None,
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """Retrieve broadly, then ensure each decision-critical source family is represented."""

        k = k or self.settings.top_k
        unique_keys = list(dict.fromkeys(source_keys))
        query = (
            description
            + " "
            + " ".join(SOURCE_QUERIES[key] for key in unique_keys if key in SOURCE_QUERIES)
        )
        queries = [query]
        evidence = self.search(query, k=max(k, min(12, len(unique_keys))))
        present = {record["source_key"] for record in evidence}

        # Metadata-constrained supplemental retrieval prevents a broad semantic match
        # from displacing an exact controlling provision.
        for key in unique_keys:
            if key in present or key not in SOURCE_QUERIES:
                continue
            source_query = SOURCE_QUERIES[key]
            queries.append(source_query)
            candidates = [
                dict(item, score=0.0)
                for item in self.records
                if item["source_key"] == key and not item.get("superseded", False)
            ]
            if candidates:
                query_tokens = set(_bm25_tokens(source_query))
                best_candidate = max(
                    candidates,
                    key=lambda item: len(
                        query_tokens.intersection(
                            _bm25_tokens(
                                f"{item.get('document', '')} {item.get('section', '')} {item['text']}"
                            )
                        )
                    ),
                )
                evidence.append(best_candidate)
                present.add(key)

        deduplicated = {record["chunk_id"]: record for record in evidence}
        ordered = sorted(deduplicated.values(), key=lambda item: item.get("score", 0), reverse=True)
        best_by_key: dict[str, dict[str, Any]] = {}
        for record in ordered:
            best_by_key.setdefault(record["source_key"], record)
        essentials = [best_by_key[key] for key in unique_keys if key in best_by_key]
        essential_ids = {record["chunk_id"] for record in essentials}
        extras = [record for record in ordered if record["chunk_id"] not in essential_ids]
        limit = max(k, len(unique_keys))
        return queries, (essentials + extras)[:limit]


@lru_cache(maxsize=1)
def get_retriever() -> HybridRegulatoryRetriever:
    return HybridRegulatoryRetriever()
