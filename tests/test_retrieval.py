from regulation_navigator.config import Settings
from regulation_navigator.retrieval import HybridRegulatoryRetriever


def test_hybrid_retrieval_preserves_exact_rule_identifier(tmp_path):
    settings = Settings(chroma_dir=tmp_path / "chroma", top_k=5)
    retriever = HybridRegulatoryRetriever(settings)
    results = retriever.search("How does EU MDR Rule 11 classify diagnostic software?", k=5)
    assert any("Rule 11" in item["section"] for item in results)


def test_assessment_retrieval_covers_requested_source_family(tmp_path):
    settings = Settings(chroma_dir=tmp_path / "chroma", top_k=5)
    retriever = HybridRegulatoryRetriever(settings)
    _, results = retriever.retrieve_for_assessment(
        "software analyzes CT images for stroke diagnosis",
        ["fda_device_definition", "fda_cds", "imdrf_n12"],
    )
    keys = {item["source_key"] for item in results}
    assert {"fda_device_definition", "fda_cds", "imdrf_n12"}.issubset(keys)
