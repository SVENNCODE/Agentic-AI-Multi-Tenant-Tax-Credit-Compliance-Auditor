import pytest

from app.domain.schemas import (
    ResidencyDetermination,
    ResidencyStatus,
    AuditTrailStep,
    QuestionnaireInput,
    VisaType,
)
from app.domain.nj_engine import evaluate_nj_deductions

def make_residency(status: ResidencyStatus, **overrides) -> ResidencyDetermination:
    defaults = dict(
        status=status,
        is_exempt_individual=(status == ResidencyStatus.NONRESIDENT_ALIEN),
        exempt_years_used=0,
        spt_weighted_days=0.0,
        target_form="Form 1040" if status == ResidencyStatus.RESIDENT_ALIEN else "Form 1040-NR",
        audit_trail=[AuditTrailStep(rule="test setup", passed=True, details="test fixture")],
    )
    defaults.update(overrides)
    return ResidencyDetermination(**defaults)

def make_questionnaire(**overrides) -> QuestionnaireInput:
    defaults = dict(
        tax_year=2025,
        state_of_residence="NJ",
        filing_status="SINGLE",
        citizenship_country="IND",
        us_entry_date="2021-08-15",
        current_visa_type=VisaType.F1,
        is_fulltime_student=True,
        employment_type="W2",
        spouse_is_us_citizen_or_resident=None,
        visa_status_periods=[],
        days_present_current_year=0,
        days_present_prior_year=0,
        days_present_two_years_prior=0,
        annual_income=30000.0,
        number_of_employers=1,
        scholarship_amount=0.0,
        tuition_paid=8000.0,
        has_education_expenses=True,
        has_childcare_expenses=False,
        has_medical_expenses=False,
        has_charitable_donations=False,
        has_retirement_contributions=False,
        has_valid_ssn=True,
        tuition_paid_to_nj=True,
    )
    defaults.update(overrides)
    return QuestionnaireInput(**defaults)

def find_result(results, rule_code):
    """Helper"""
    matches = [r for r in results if r.rule_code == rule_code]
    assert matches, f"No result found for rule_code={rule_code}"
    return matches[0]

def test_non_nj_resident_ineligible():
    residency = make_residency(ResidencyStatus.RESIDENT_ALIEN)
    questionnaire = make_questionnaire(state_of_residence="NY")
    results = evaluate_nj_deductions(residency, questionnaire)
    assert len(results) == 1
    assert results[0].status == "INELIGIBLE"
    assert results[0].rule_code == "NJ_RESIDENCY_REQ"

def test_income_above_200k_ineligible():
    residency = make_residency(ResidencyStatus.RESIDENT_ALIEN)
    questionnaire = make_questionnaire(annual_income=250000.0)
    results = evaluate_nj_deductions(residency, questionnaire)
    result = find_result(results, "NJ_TUITION_DEDUCTION")
    assert result.status == "INELIGIBLE"
    assert "$200,000" in result.reason

def test_out_of_state_tuition_ineligible():
    residency = make_residency(ResidencyStatus.RESIDENT_ALIEN)
    questionnaire = make_questionnaire(tuition_paid_to_nj=False)
    results = evaluate_nj_deductions(residency, questionnaire)
    result = find_result(results, "NJ_TUITION_DEDUCTION")
    assert result.status == "INELIGIBLE"
    assert "in-State" in result.reason

def test_institution_state_unknown_needs_documentation():
    residency = make_residency(ResidencyStatus.RESIDENT_ALIEN)
    questionnaire = make_questionnaire(tuition_paid_to_nj=None)
    results = evaluate_nj_deductions(residency, questionnaire)
    result = find_result(results, "NJ_TUITION_DEDUCTION")
    assert result.status == "NEEDS_DOCUMENTATION"
    assert "Confirm whether tuition" in result.reason

def test_nra_with_nj_tuition_needs_documentation():
    residency = make_residency(ResidencyStatus.NONRESIDENT_ALIEN)
    questionnaire = make_questionnaire(tuition_paid_to_nj=True)
    results = evaluate_nj_deductions(residency, questionnaire)
    result = find_result(results, "NJ_TUITION_DEDUCTION")
    assert result.status == "NEEDS_DOCUMENTATION"
    assert "NJ-1040NR" in result.reason

def test_resident_full_time_in_state_eligible():
    residency = make_residency(ResidencyStatus.RESIDENT_ALIEN)
    questionnaire = make_questionnaire(
        tuition_paid_to_nj=True,
        is_fulltime_student=True,
        tuition_paid=8000.0,
    )
    results = evaluate_nj_deductions(residency, questionnaire)
    result = find_result(results, "NJ_TUITION_DEDUCTION")
    assert result.status == "ELIGIBLE"
    assert result.estimated_amount == pytest.approx(8000.0)

def test_tuition_deduction_capped_at_10000():
    residency = make_residency(ResidencyStatus.RESIDENT_ALIEN)
    questionnaire = make_questionnaire(
        tuition_paid_to_nj=True,
        is_fulltime_student=True,
        tuition_paid=14000.0,
    )
    results = evaluate_nj_deductions(residency, questionnaire)
    result = find_result(results, "NJ_TUITION_DEDUCTION")
    assert result.status == "ELIGIBLE"
    assert result.estimated_amount == pytest.approx(10000.0)

def test_no_tuition_or_not_fulltime_ineligible():
    residency = make_residency(ResidencyStatus.RESIDENT_ALIEN)
    questionnaire = make_questionnaire(tuition_paid=0.0)

    results = evaluate_nj_deductions(residency, questionnaire)

    result = find_result(results, "NJ_TUITION_DEDUCTION")
    assert result.status == "INELIGIBLE"