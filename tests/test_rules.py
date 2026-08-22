from regulation_navigator.models import AssessmentInput
from regulation_navigator.rules import (
    analyze_us_status,
    classify_iec62304,
    classify_imdrf_samd,
    classify_software_scope,
    collect_follow_up_questions,
    normalize_input,
)


def state_for(**values):
    payload = AssessmentInput(software_description=values.pop("software_description"), **values)
    state = {"input": payload.model_dump()}
    state.update(normalize_input(state))
    state.update(classify_software_scope(state))
    state.update(analyze_us_status(state))
    return state


def test_embedded_robot_is_not_samd_and_is_preliminary_class_c():
    state = state_for(
        software_description="Embedded software controls a surgical robot used to treat a patient.",
        medical_purpose=True,
        part_of_medical_device=True,
        standalone=False,
        hazard_severity="death_or_serious_injury",
    )
    assert "Software in a Medical Device" in state["software_category"]
    assert "Likely Device Software Function" in state["us_device_status"]
    assert "Not SaMD" in classify_imdrf_samd(state)["samd_category"]
    assert "Class C" in classify_iec62304(state)["iec62304_class"]


def test_non_device_cds_requires_all_screened_facts():
    state = state_for(
        software_description="Clinical decision support offers treatment options to a physician.",
        medical_purpose=True,
        standalone=True,
        cds=True,
        intended_user="clinician",
        analyzes_medical_image_or_signal=False,
        provides_specific_output_or_directive=False,
        hcp_can_independently_review_basis=True,
    )
    assert state["us_device_status"] == "Potential Non-Device CDS"


def test_unknown_cds_fact_generates_question_instead_of_conclusion():
    state = state_for(
        software_description="Clinical decision support gives a recommendation to a physician.",
        medical_purpose=True,
        standalone=True,
        cds=True,
        intended_user="clinician",
        analyzes_medical_image_or_signal=False,
        provides_specific_output_or_directive=False,
    )
    assert "indeterminate" in state["us_device_status"].lower()
    state.update(collect_follow_up_questions(state))
    assert any("independently review" in question for question in state["follow_up_questions"])


def test_imdrf_matrix_category_four():
    state = state_for(
        software_description="Standalone software diagnoses a critical condition.",
        medical_purpose=True,
        standalone=True,
        information_significance="treat_or_diagnose",
        condition_severity="critical",
    )
    assert "Category IV" in classify_imdrf_samd(state)["samd_category"]
