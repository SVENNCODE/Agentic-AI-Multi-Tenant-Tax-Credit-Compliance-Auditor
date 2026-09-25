"""
Regression tests for evaluate_india_treaty_benefit().
Tests Article 21(2) US-India Income Tax Treaty standard deduction eligibility
without database dependencies.
"""

import pytest

from app.domain.schemas import (
    CreditEvaluationResult,
    QuestionnaireInput,
    ResidencyDetermination,
    ResidencyStatus,
    AuditTrailStep,
    VisaType,
)
from app.domain.treaty_india_engine import evaluate_india_treaty_benefit

def make_residency(status: ResidencyStatus) -> ResidencyDetermination:
    return ResidencyDetermination(
        status=status,
        is_exempt_individual=(status == ResidencyStatus.NONRESIDENT_ALIEN),
        exempt_years_used=0,
        spt_weighted_days=0.0,
        target_form="Form 1040-NR" if status != ResidencyStatus.RESIDENT_ALIEN else "Form 1040",
        audit_trail=[AuditTrailStep(rule="test setup", passed=True, details="test fixture")],
    )

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
        annual_income=15000.0,
        number_of_employers=1,
        scholarship_amount=0.0,
        tuition_paid=14000.0,
        has_education_expenses=True,
        has_childcare_expenses=False,
        has_medical_expenses=False,
        has_charitable_donations=False,
        has_retirement_contributions=False,
        has_valid_ssn=True,
        prior_years_aotc_claimed=0,
    )
    defaults.update(overrides)
    return QuestionnaireInput(**defaults)

def test_non_indian_citizen_ineligible():
    residency = make_residency(ResidencyStatus.NONRESIDENT_ALIEN)
    questionnaire = make_questionnaire(citizenship_country="CHN")
    result = evaluate_india_treaty_benefit(residency, questionnaire)
    assert result.status == "INELIGIBLE"
    assert result.rule_code == "US_IND_ART21_2"
    assert "exclusively restricted to citizens/nationals of India" in result.reason
    assert result.estimated_amount == 0.0

def test_h1b_visa_ineligible_for_student_treaty():
    residency = make_residency(ResidencyStatus.NONRESIDENT_ALIEN)
    questionnaire = make_questionnaire(
        citizenship_country="IND",
        current_visa_type=VisaType.H1B,
    )
    result = evaluate_india_treaty_benefit(residency, questionnaire)
    assert result.status == "INELIGIBLE"
    assert "requires active F-1 or J-1" in result.reason
    assert result.estimated_amount == 0.0

def test_resident_alien_treaty_not_applicable():
    residency = make_residency(ResidencyStatus.RESIDENT_ALIEN)
    questionnaire = make_questionnaire(
        citizenship_country="IND",
        current_visa_type=VisaType.F1,
    )
    result = evaluate_india_treaty_benefit(residency, questionnaire)
    assert result.status == "NOT_APPLICABLE"
    assert "already classified as a Resident Alien" in result.reason
    assert result.estimated_amount == 0.0

def test_indian_f1_nra_eligible_for_treaty_standard_deduction():
    residency = make_residency(ResidencyStatus.NONRESIDENT_ALIEN)
    questionnaire = make_questionnaire(
        citizenship_country="IND",
        current_visa_type=VisaType.F1,
    )
    result = evaluate_india_treaty_benefit(residency, questionnaire)
    assert result.status == "ELIGIBLE"
    assert result.source_type == "TREATY_BENEFIT"
    assert result.rule_code == "US_IND_ART21_2"
    assert result.estimated_amount == pytest.approx(15750.0)

def test_indian_j1_nra_eligible_for_treaty():
    residency = make_residency(ResidencyStatus.NONRESIDENT_ALIEN)
    questionnaire = make_questionnaire(
        citizenship_country="IND",
        current_visa_type=VisaType.J1,
    )
    result = evaluate_india_treaty_benefit(residency, questionnaire)
    assert result.status == "ELIGIBLE"
    assert result.estimated_amount == pytest.approx(15750.0)

def test_indian_f1_dual_status_needs_documentation():
    residency = make_residency(ResidencyStatus.DUAL_STATUS)
    questionnaire = make_questionnaire(
        citizenship_country="IND",
        current_visa_type=VisaType.F1,
    )
    result = evaluate_india_treaty_benefit(residency, questionnaire)
    assert result.status == "NEEDS_DOCUMENTATION"
    assert result.source_type == "TREATY_BENEFIT"
    assert result.rule_code == "US_IND_ART21_2"
    assert "Taxpayer has a dual-status tax year" in result.reason
    assert result.estimated_amount == 0.0