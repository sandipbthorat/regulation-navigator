"""Streamlit interface for the Medical Device Software Regulatory Navigator."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from regulation_navigator.graph import run_assessment
from regulation_navigator.models import AssessmentInput

load_dotenv()
st.set_page_config(page_title="Regulation Navigator", page_icon="🧭", layout="wide")


def tri_state(label: str, help_text: str | None = None):
    value = st.selectbox(label, ["Unknown", "Yes", "No"], help=help_text)
    return {"Unknown": None, "Yes": True, "No": False}[value]


st.title("Medical Device Software Regulatory Navigator")
st.caption(
    "Preliminary, source-grounded screening across FDA software policy, EU MDR Rule 11, "
    "IMDRF SaMD, IEC 62304, and ISO 14971. Not legal advice."
)

with st.form("assessment"):
    description = st.text_area(
        "Describe one software function",
        value="Software running on a surgical robotic platform that analyzes sensor information and provides an alert to the surgeon.",
        height=130,
        help="Analyze one function at a time. Include users, inputs, outputs, hardware relationship, and failure consequences when known.",
    )
    intended_use = st.text_area("Formal intended-use statement (optional)", height=80)

    st.subheader("Core facts")
    core_columns = st.columns(4)
    with core_columns[0]:
        medical_purpose = tri_state("Medical purpose?")
        part_of_device = tri_state("Part of a hardware device?")
    with core_columns[1]:
        standalone = tri_state("Independent of hardware?")
        controls_device = tri_state("Controls device hardware?")
    with core_columns[2]:
        cds = tri_state("Clinical decision support?")
        data_only = tri_state("Only transfer/store/display?")
    with core_columns[3]:
        ai_ml = tri_state("Uses AI/ML?")
        network_connected = tri_state("Network/cloud connected?")

    with st.expander("CDS, SaMD, and risk details"):
        detail_columns = st.columns(3)
        with detail_columns[0]:
            intended_user = st.selectbox(
                "Intended user",
                ["unknown", "clinician", "patient_or_caregiver", "manufacturer", "other"],
            )
            image_signal = tri_state("Analyzes medical image/signal?")
            specific_directive = tri_state("Specific output/directive?")
            independent_review = tri_state("HCP can review recommendation basis?")
        with detail_columns[1]:
            significance = st.selectbox(
                "Significance of information",
                [
                    "unknown",
                    "treat_or_diagnose",
                    "drive_clinical_management",
                    "inform_clinical_management",
                ],
            )
            condition = st.selectbox(
                "Health-care condition",
                ["unknown", "critical", "serious", "non_serious"],
            )
        with detail_columns[2]:
            hazard = st.selectbox(
                "Worst failure consequence",
                ["unknown", "death_or_serious_injury", "non_serious_injury", "no_injury"],
            )
            eu_consequence = st.selectbox(
                "EU: consequence of wrong diagnostic/therapeutic decision",
                [
                    "unknown",
                    "death_or_irreversible_deterioration",
                    "serious_deterioration_or_surgical_intervention",
                    "other",
                ],
            )

    submitted = st.form_submit_button("Run preliminary assessment", type="primary")

if submitted:
    payload = AssessmentInput(
        software_description=description,
        intended_use=intended_use,
        medical_purpose=medical_purpose,
        part_of_medical_device=part_of_device,
        standalone=standalone,
        controls_hardware_device=controls_device,
        cds=cds,
        data_only=data_only,
        ai_ml=ai_ml,
        network_connected=network_connected,
        intended_user=intended_user,
        analyzes_medical_image_or_signal=image_signal,
        provides_specific_output_or_directive=specific_directive,
        hcp_can_independently_review_basis=independent_review,
        information_significance=significance,
        condition_severity=condition,
        hazard_severity=hazard,
        eu_decision_consequence=eu_consequence,
    )
    with st.spinner("Running the classification graph and validating citations…"):
        try:
            result = run_assessment(payload)
        except Exception as exc:  # noqa: BLE001 - keep the interactive UI alive at its boundary.
            st.error(f"Assessment failed: {exc}")
            st.stop()

    classification = result["classification"]
    tabs = st.tabs(["Assessment", "Applicable sources", "Evidence and quality"])
    with tabs[0]:
        if result["answer_status"].startswith("refused"):
            st.error(result["narrative"])
        else:
            st.info(result["narrative"])
        st.subheader("Preliminary classification")
        left, right = st.columns(2)
        with left:
            st.markdown(f"**Software category**  \n{classification['software_category']}")
            st.markdown(f"**U.S. FDA status**  \n{classification['us_fda_status']}")
            st.markdown(f"**CDS status**  \n{classification['cds_status']}")
        with right:
            st.markdown(f"**IMDRF SaMD**  \n{classification['imdrf_samd']}")
            st.markdown(f"**IEC 62304**  \n{classification['iec_62304']}")
            st.markdown(f"**EU MDR**  \n{classification['eu_mdr']}")

        if result["rationale"]:
            st.subheader("Rationale")
            for item in result["rationale"]:
                st.markdown(f"- {item}")

        if result["follow_up_questions"]:
            st.subheader("Information still required")
            for index, question in enumerate(result["follow_up_questions"], 1):
                st.markdown(f"{index}. {question}")

        st.warning(result["disclaimer"])

    with tabs[1]:
        rows = [
            {
                "Authority": item["authority"],
                "Document": item["document"],
                "Section": item["section"],
                "Status": item["status"],
                "Why it matters": item["applicability"],
                "Citation": item["citation"],
            }
            for item in result["applicable_requirements"]
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    with tabs[2]:
        validation = result["citation_validation"]
        metric_columns = st.columns(4)
        metric_columns[0].metric("Validated citations", validation["valid_citation_count"])
        metric_columns[1].metric(
            "Applicability-source coverage",
            f"{validation['applicability_source_coverage']:.0%}",
        )
        metric_columns[2].metric(
            "Claim-level faithfulness",
            f"{result['grounding']['claim_level_faithfulness']:.0%}",
        )
        metric_columns[3].metric("Latency", f"{result['latency_seconds']:.2f}s")
        freshness = result["freshness_validation"]
        if freshness["status"] == "current":
            st.success(
                f"Corpus review is current: reviewed {freshness['reviewed_at']} "
                f"({freshness['age_days']} days ago; {freshness['freshness_sla_days']}-day SLA)."
            )
        else:
            st.error(
                "Corpus freshness gate failed. Do not rely on the assessment until the index is reviewed."
            )
        for warning in validation["warnings"]:
            st.warning(warning)
        for source in result["evidence"]:
            with st.expander(f"[{source['chunk_id']}] {source['document']} — {source['section']}"):
                st.write(source["text"])
                st.caption(
                    f"{source['authority']} · {source['document_type']} · {source['status']} · {source['date']}"
                )
                st.link_button("Open official/source page", source["source_url"])
