"""LangGraph orchestration for deterministic classification and cited RAG."""

from __future__ import annotations

import time
from typing import Literal

from langgraph.graph import END, START, StateGraph

from regulation_navigator.citations import validate_citations
from regulation_navigator.grounding import build_grounded_answer
from regulation_navigator.llm import extract_facts
from regulation_navigator.models import AssessmentInput, RegulatoryState
from regulation_navigator.render import compose_assessment
from regulation_navigator.retrieval import get_retriever
from regulation_navigator.rules import (
    analyze_us_status,
    classify_eu_mdr,
    classify_iec62304,
    classify_imdrf_samd,
    classify_software_scope,
    collect_follow_up_questions,
    determine_applicability,
)


def route_cds(state: RegulatoryState) -> Literal["cds", "general"]:
    return "cds" if state["facts"].get("cds") is True else "general"


def analyze_cds_path(state: RegulatoryState):
    return analyze_us_status(state)


def analyze_general_us_path(state: RegulatoryState):
    return analyze_us_status(state)


def retrieve_regulatory_evidence(state: RegulatoryState):
    facts = state["facts"]
    description = f"{facts.get('software_description', '')} {facts.get('intended_use', '')}".strip()
    claim_source_keys = [
        "fda_device_definition",
        "fda_device_software_policy",
        "imdrf_n10",
        "iec_62304",
        "eu_mdr_rule11",
    ]
    queries, evidence = get_retriever().retrieve_for_assessment(
        description=description,
        source_keys=list(
            dict.fromkeys(state.get("applicable_regulations", []) + claim_source_keys)
        ),
    )
    return {"retrieval_queries": queries, "retrieved_sources": evidence}


def build_graph():
    builder = StateGraph(RegulatoryState)
    builder.add_node("extract_facts", extract_facts)
    builder.add_node("classify_software_scope", classify_software_scope)
    builder.add_node("analyze_cds_path", analyze_cds_path)
    builder.add_node("analyze_general_us_path", analyze_general_us_path)
    builder.add_node("classify_imdrf_samd", classify_imdrf_samd)
    builder.add_node("classify_iec62304", classify_iec62304)
    builder.add_node("classify_eu_mdr", classify_eu_mdr)
    builder.add_node("collect_follow_up_questions", collect_follow_up_questions)
    builder.add_node("determine_applicability", determine_applicability)
    builder.add_node("retrieve_regulatory_evidence", retrieve_regulatory_evidence)
    builder.add_node("validate_citations", validate_citations)
    builder.add_node("build_grounded_answer", build_grounded_answer)
    builder.add_node("compose_assessment", compose_assessment)

    builder.add_edge(START, "extract_facts")
    builder.add_edge("extract_facts", "classify_software_scope")
    builder.add_conditional_edges(
        "classify_software_scope",
        route_cds,
        {"cds": "analyze_cds_path", "general": "analyze_general_us_path"},
    )
    builder.add_edge("analyze_cds_path", "classify_imdrf_samd")
    builder.add_edge("analyze_general_us_path", "classify_imdrf_samd")
    builder.add_edge("classify_imdrf_samd", "classify_iec62304")
    builder.add_edge("classify_iec62304", "classify_eu_mdr")
    builder.add_edge("classify_eu_mdr", "collect_follow_up_questions")
    builder.add_edge("collect_follow_up_questions", "determine_applicability")
    builder.add_edge("determine_applicability", "retrieve_regulatory_evidence")
    builder.add_edge("retrieve_regulatory_evidence", "validate_citations")
    builder.add_edge("validate_citations", "build_grounded_answer")
    builder.add_edge("build_grounded_answer", "compose_assessment")
    builder.add_edge("compose_assessment", END)
    return builder.compile()


graph = build_graph()


def run_assessment(assessment_input: AssessmentInput | dict) -> dict:
    started = time.perf_counter()
    validated = (
        assessment_input
        if isinstance(assessment_input, AssessmentInput)
        else AssessmentInput.model_validate(assessment_input)
    )
    final_state = graph.invoke({"input": validated.model_dump()})
    assessment = final_state["assessment"]
    assessment["latency_seconds"] = round(time.perf_counter() - started, 4)
    assessment["latency_target_seconds"] = 5.0
    assessment["latency_target_met"] = assessment["latency_seconds"] <= 5.0
    return assessment
