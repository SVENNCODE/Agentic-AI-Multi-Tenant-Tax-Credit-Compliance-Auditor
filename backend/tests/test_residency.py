from datetime import date
import pytest
from app.domain.schemas import TaxPayerInput, VisaPeriod, VisaType, ResidencyStatus
from app.domain.calculator import determine_residency

def test_first_year_f1_student_is_nra():
    """IRS Pub 519 Scenario: An F-1 student arriving in current tax year is an NRA."""
    taxpayer = TaxPayerInput(
        tax_year=2025,
        citizenship_country="India",
        entry_date=date(2025, 8, 15),
        visa_history=[
            VisaPeriod(visa_type=VisaType.F1, start_date=date(2025, 8, 15))
        ],
        days_present_current_year=138,
        days_present_prior_year=0,
        days_present_two_years_prior=0
    )

    result = determine_residency(taxpayer)

    assert result.status == ResidencyStatus.NONRESIDENT_ALIEN
    assert result.is_exempt_individual is True
    assert result.exempt_years_used == 0
    assert result.target_form == "Form 1040-NR"

def test_sixth_year_f1_student_spt_resident_alien():
    """F-1 student in US since 2020 (5 exempt years used: 2020-2024). Evaluated for 2025."""
    taxpayer = TaxPayerInput(
        tax_year=2025,
        citizenship_country="South Korea",
        entry_date=date(2020, 8, 20),
        visa_history=[
            VisaPeriod(visa_type=VisaType.F1, start_date=date(2020, 8, 20))
        ],
        days_present_current_year=200,
        days_present_prior_year=300,
        days_present_two_years_prior=300
    )

    result = determine_residency(taxpayer)

    assert result.status == ResidencyStatus.RESIDENT_ALIEN
    assert result.is_exempt_individual is False
    assert result.exempt_years_used == 5
    assert result.target_form == "Form 1040"