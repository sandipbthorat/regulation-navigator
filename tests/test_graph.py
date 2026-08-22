from regulation_navigator.graph import run_assessment
from regulation_navigator.retrieval import get_retriever


def test_graph_returns_structured_cited_assessment(monkeypatch, tmp_path):
    monkeypatch.setenv("REGNAV_CHROMA_DIR", str(tmp_path / "chroma"))
    get_retriever.cache_clear()
    result = run_assessment(
        {
            "software_description": "Standalone AI software detects stroke from CT images for a radiologist.",
            "medical_purpose": True,
            "standalone": True,
            "cds": True,
            "ai_ml": True,
            "network_connected": False,
            "intended_user": "clinician",
            "analyzes_medical_image_or_signal": True,
            "provides_specific_output_or_directive": True,
            "hcp_can_independently_review_basis": False,
            "information_significance": "treat_or_diagnose",
            "condition_severity": "critical",
            "hazard_severity": "death_or_serious_injury",
        }
    )
    assert "Likely Device Software Function" in result["classification"]["us_fda_status"]
    assert result["citation_validation"]["valid_citation_count"] > 0
    assert all(item["source_url"].startswith("https://") for item in result["evidence"])
    assert result["grounding"]["claim_level_faithfulness"] >= 0.95
    assert result["grounding"]["invalid_inline_citations"] == []
    assert result["answer_status"] in {"grounded_answer", "answer_with_caveats"}
    assert result["latency_target_met"] is True


def test_graph_refuses_out_of_scope_request(monkeypatch, tmp_path):
    monkeypatch.setenv("REGNAV_CHROMA_DIR", str(tmp_path / "chroma"))
    get_retriever.cache_clear()
    result = run_assessment(
        {"software_description": "Please explain how to bake a sourdough loaf at home."}
    )
    assert result["answer_status"] == "refused_out_of_scope"
    assert "can’t support" in result["narrative"]
