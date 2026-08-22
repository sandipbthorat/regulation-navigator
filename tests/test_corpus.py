from regulation_navigator.config import PROJECT_ROOT
from regulation_navigator.corpus import load_jsonl
from regulation_navigator.freshness import audit_corpus_freshness


def test_starter_corpus_has_complete_current_metadata():
    records = load_jsonl(PROJECT_ROOT / "data" / "corpus" / "starter_corpus.jsonl")
    assert len(records) >= 20
    assert len({record["chunk_id"] for record in records}) == len(records)
    assert all(record["source_url"].startswith("https://") for record in records)
    assert all(record["superseded"] is False for record in records)


def test_starter_corpus_marks_draft_and_licensed_material():
    records = load_jsonl(PROJECT_ROOT / "data" / "corpus" / "starter_corpus.jsonl")
    by_key = {record["source_key"]: record for record in records}
    assert "Draft" in by_key["fda_ai_lifecycle"]["status"]
    assert "licensed" in by_key["iec_62304"]["document_type"].lower()
    assert "licensed" in by_key["iso_14971"]["document_type"].lower()


def test_freshness_manifest_covers_active_corpus():
    audit = audit_corpus_freshness()
    assert audit["status"] == "current"
    assert audit["missing_source_keys"] == []
    assert audit["source_family_count"] == 19
