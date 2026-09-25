from datetime import date

import pytest
from pydantic import ValidationError

from app.domain.calculator import determine_residency
from app.domain.credit_engine import evaluate_education_credit
from app.domain.nj_engine import evaluate_nj_deductions
from app.domain.schemas import (
    EmploymentType,
    FederalCreditRule,
    ResidencyStatus,
    TaxPayerInput,
    VisaPeriod,
    VisaType,
)
from tests.test_treaty_india_engine import make_questionnaire, make_residency


def taxpayer(**overrides):
    base = dict(
        tax_year=2025,
        citizenship_country="IND",
        entry_date=date(2022, 8, 15),
        visa_history=[VisaPeriod(visa_type=VisaType.F1, start_date=date(2022, 8, 15))],
        days_present_current_year=300,
        days_present_prior_year=300,
        days_present_two_years_prior=120,
    )
    base.update(overrides)
    return TaxPayerInput(**base)


def test_clean_input_is_not_undetermined():
    assert determine_residency(taxpayer()).status != ResidencyStatus.UNDETERMINED


@pytest.mark.parametrize("overrides", [
    {"entry_date": None},
    {"entry_date": date(2026, 1, 5)},
    {"visa_history": []},
    {"visa_history": [
        VisaPeriod(visa_type=VisaType.F1, start_date=date(2022, 8, 15), end_date=date(2025, 12, 31)),
        VisaPeriod(visa_type=VisaType.H1B, start_date=date(2024, 1, 1)),
    ]},
    {"visa_history": [VisaPeriod(visa_type=VisaType.F1, start_date=date(2020, 1, 1))]},
])
def test_ambiguous_inputs_are_undetermined(overrides):
    result = determine_residency(taxpayer(**overrides))
    assert result.status == ResidencyStatus.UNDETERMINED
    assert result.audit_trail[0].rule == "Input Consistency Check"
    assert result.audit_trail[0].passed is False


def test_back_to_back_status_change_is_still_dual_status_not_undetermined():
    result = determine_residency(taxpayer(visa_history=[
        VisaPeriod(visa_type=VisaType.F1, start_date=date(2022, 8, 15), end_date=date(2025, 6, 30)),
        VisaPeriod(visa_type=VisaType.H1B, start_date=date(2025, 6, 30)),
    ]))
    assert result.status == ResidencyStatus.DUAL_STATUS


AOTC = FederalCreditRule(
    tax_year=2025, credit_code="AOTC", credit_name="American Opportunity Tax Credit",
    max_credit_amount=2500, refundable_percentage=0.4, max_refundable_amount=1000,
    expense_cap=4000, max_years_claimable=4, requires_ssn=True,
    allows_nonresident_aliens=False, min_enrollment_status="half_time",
    magi_phaseout_single_start=80000, magi_phaseout_single_end=90000,
    magi_phaseout_mfj_start=160000, magi_phaseout_mfj_end=180000,
)


def test_downstream_engines_never_mark_undetermined_eligible():
    residency = make_residency(ResidencyStatus.UNDETERMINED)
    q = make_questionnaire(tuition_paid_to_nj=True)
    assert evaluate_education_credit(AOTC, residency, q).status == "NEEDS_DOCUMENTATION"
    statuses = {r.status for r in evaluate_nj_deductions(residency, q)}
    assert "ELIGIBLE" not in statuses


def test_employment_type_is_strict_enum():
    assert make_questionnaire(employment_type="STUDENT_WORKER").employment_type is EmploymentType.STUDENT_WORKER
    with pytest.raises(ValidationError):
        make_questionnaire(employment_type="freelancer")
