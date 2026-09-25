from app.domain.credit_engine import evaluate_education_credit
from app.domain.schemas import (
    FederalCreditRule,
    CreditEvaluationResult,
    ResidencyDetermination,
    QuestionnaireInput,
    ResidencyStatus,
    AuditTrailStep,
    VisaType,
)

def make_aotc_rule(**overrides) -> FederalCreditRule:
    defaults = dict(
        tax_year=2025,
        credit_code="AOTC",
        credit_name="American Opportunity Tax Credit",
        max_credit_amount=2500.0,
        refundable_percentage=0.40,
        max_refundable_amount=1000.0,
        expense_cap=4000.0,
        requires_ssn=True,
        allows_nonresident_aliens=False,
        min_enrollment_status="half_time",
        max_years_claimable=4,
        magi_phaseout_single_start=80000.0,
        magi_phaseout_single_end=90000.0,
        magi_phaseout_mfj_start=160000.0,
        magi_phaseout_mfj_end=180000.0,
    )
    defaults.update(overrides)
    return FederalCreditRule(**defaults)

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
        annual_income=50000.0,
        number_of_employers=1,
        scholarship_amount=0.0,
        tuition_paid=4000.0,
        has_education_expenses=True,
        has_childcare_expenses=False,
        has_medical_expenses=False,
        has_charitable_donations=False,
        has_retirement_contributions=False,
        has_valid_ssn=None,
    )
    defaults.update(overrides)
    return QuestionnaireInput(**defaults)

def test_real_aotc_rule_returns_needs_documentation_when_ssn_is_none():
    """
    When has_valid_ssn is None (unspecified), AOTC requires verification
    and return NEEDS_DOCUMENTATION.
    """
    rule = make_aotc_rule()
    residency = make_residency(ResidencyStatus.RESIDENT_ALIEN)

    q = make_questionnaire(
        has_education_expenses=True,
        tuition_paid=5000.0,
        annual_income=40000.0,
        is_fulltime_student=True,
        has_valid_ssn=None,
    )
    result = evaluate_education_credit(rule, residency, q)
    assert result.status == "NEEDS_DOCUMENTATION"
    assert "SSN" in result.reason or "Verification required" in result.reason

def test_real_aotc_rule_ineligible_when_has_valid_ssn_is_false():
    """
    When taxpayer explicitly indicates has_valid_ssn=False,
    AOTC evaluation immediately returns INELIGIBLE per IRC Sec. 25A.
    """
    rule = make_aotc_rule()
    residency = make_residency(ResidencyStatus.RESIDENT_ALIEN)
    q = make_questionnaire(
        has_education_expenses=True,
        tuition_paid=5000.0,
        annual_income=40000.0,
        is_fulltime_student=True,
        has_valid_ssn=False,
    )
    result = evaluate_education_credit(rule, residency, q)
    assert result.status == "INELIGIBLE"
    assert "requires a valid SSN issued by the return due date" in result.reason
    assert "an ITIN does not qualify" in result.reason


def test_aotc_returns_needs_documentation_when_prior_years_claimed_is_none():
    """
    When prior_years_aotc_claimed is None, evaluate_education_credit must return
    NEEDS_DOCUMENTATION to confirm prior claims against the 4-year limit.
    """
    rule = make_aotc_rule()
    residency = make_residency(ResidencyStatus.RESIDENT_ALIEN)
    q = make_questionnaire(
        has_education_expenses=True,
        tuition_paid=4000.0,
        annual_income=50000.0,
        is_fulltime_student=True,
        has_valid_ssn=True,
        prior_years_aotc_claimed=None,
    )
    result = evaluate_education_credit(rule, residency, q)
    assert result.status == "NEEDS_DOCUMENTATION"
    assert "4-year" in result.reason
    assert "lifetime limit" in result.reason


def test_aotc_ineligible_when_prior_years_claimed_reaches_limit():
    """
    When prior_years_aotc_claimed equals or exceeds max_years_claimable (4),
    AOTC evaluation returns INELIGIBLE.
    """
    rule = make_aotc_rule()
    residency = make_residency(ResidencyStatus.RESIDENT_ALIEN)
    q = make_questionnaire(
        has_education_expenses=True,
        tuition_paid=4000.0,
        annual_income=50000.0,
        is_fulltime_student=True,
        has_valid_ssn=True,
        prior_years_aotc_claimed=4,
    )
    result = evaluate_education_credit(rule, residency, q)
    assert result.status == "INELIGIBLE"
    assert "has already been claimed 4 times" in result.reason
    assert "reaching its 4-year lifetime limit" in result.reason


def test_aotc_eligible_when_prior_years_claimed_under_limit():
    """
    When prior_years_aotc_claimed is less than max_years_claimable
    and all other checks pass, evaluation falls through to ELIGIBLE.
    """
    rule = make_aotc_rule(requires_ssn=False)
    residency = make_residency(ResidencyStatus.RESIDENT_ALIEN)

    q = make_questionnaire(
        has_education_expenses=True,
        tuition_paid=4000.0,
        annual_income=50000.0,
        is_fulltime_student=True,
        has_valid_ssn=True,
        prior_years_aotc_claimed=2,
    )
    result = evaluate_education_credit(rule, residency, q)
    assert result.status == "ELIGIBLE"
    assert result.estimated_amount == 2500.0