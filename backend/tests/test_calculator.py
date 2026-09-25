"""
Regression tests for the residency determination engine.

Each test locks in a scenario that was manually verified through the actual
questionnaire UI during development including two bugs found and
fixed (the H-1B exemption bug, and the mid-year dual-status gap).
"""

from datetime import date

import pytest

from app.domain.schemas import TaxPayerInput, VisaPeriod, ResidencyStatus, VisaType
from app.domain.calculator import determine_residency


def make_input(
    tax_year: int,
    citizenship_country: str = "IND",
    entry_date: date = date(2021, 8, 15),
    visa_history: list[VisaPeriod] | None = None,
    days_current: int = 0,
    days_prior: int = 0,
    days_two_prior: int = 0,
) -> TaxPayerInput:
    """helper"""
    return TaxPayerInput(
        tax_year=tax_year,
        citizenship_country=citizenship_country,
        entry_date=entry_date,
        visa_history=visa_history or [],
        days_present_current_year=days_current,
        days_present_prior_year=days_prior,
        days_present_two_years_prior=days_two_prior,
    )
# 1. Exempt, continuous presence, early exempt years, no SPT needed
def test_exempt_continuous_early_years():
    input_data = make_input(
        tax_year=2023,
        entry_date=date(2021, 8, 15),
        visa_history=[
            VisaPeriod(visa_type=VisaType.F1, start_date=date(2021, 8, 15), end_date=None),
        ],
        days_current=365,
        days_prior=365,
        days_two_prior=0,
    )
    result = determine_residency(input_data)

    assert result.status == ResidencyStatus.NONRESIDENT_ALIEN
    assert result.is_exempt_individual is True
    assert result.exempt_years_used == 2
# 2. Exempt, with a summer departure so it should not affect exempt-year count
def test_exempt_with_summer_departure():
    input_data = make_input(
        tax_year=2023,
        entry_date=date(2021, 8, 15),
        visa_history=[
            VisaPeriod(visa_type=VisaType.F1, start_date=date(2021, 8, 15), end_date=None),
        ],
        days_current=300,  # left for 65 days over the summer
        days_prior=365,
        days_two_prior=0,
    )
    result = determine_residency(input_data)
    assert result.status == ResidencyStatus.NONRESIDENT_ALIEN
    assert result.is_exempt_individual is True
# 3. SPT boundary ,exactly 183.0 weighted days should PASS
def test_spt_exact_183_weighted_days_passes():
    input_data = make_input(
        tax_year=2025,
        entry_date=date(2018, 1, 1),
        visa_history=[
            VisaPeriod(visa_type=VisaType.F1, start_date=date(2018, 1, 1), end_date=date(2023, 12, 31)),
        ],
        days_current=183,
        days_prior=0,
        days_two_prior=0,
    )
    result = determine_residency(input_data)

    assert result.spt_weighted_days == pytest.approx(183.0)
    assert result.status == ResidencyStatus.RESIDENT_ALIEN
# 4a. 31-day threshold  exactly 31 current-year days should PASS
def test_spt_31_days_current_year_passes_threshold():
    input_data = make_input(
        tax_year=2025,
        entry_date=date(2018, 1, 1),
        visa_history=[
            VisaPeriod(visa_type=VisaType.F1, start_date=date(2018, 1, 1), end_date=date(2023, 12, 31)),
        ],
        days_current=31,
        days_prior=365,
        days_two_prior=365,
    )
    result = determine_residency(input_data)
    assert result.status == ResidencyStatus.RESIDENT_ALIEN
# 4b. 30 days current year, fails the 31-day floor regardless of weighted total
def test_spt_30_days_current_year_fails_threshold():
    input_data = make_input(
        tax_year=2025,
        entry_date=date(2018, 1, 1),
        visa_history=[
            VisaPeriod(visa_type=VisaType.F1, start_date=date(2018, 1, 1), end_date=date(2023, 12, 31)),
        ],
        days_current=30,
        days_prior=365,
        days_two_prior=365,
    )
    result = determine_residency(input_data)
    assert result.status == ResidencyStatus.NONRESIDENT_ALIEN
# 5. Exempt years exhausted + high presence -> RESIDENT_ALIEN
def test_exhausted_exempt_years_high_presence_becomes_resident():
    input_data = make_input(
        tax_year=2025,
        entry_date=date(2020, 1, 1),
        visa_history=[
            VisaPeriod(visa_type=VisaType.F1, start_date=date(2020, 1, 1), end_date=date(2024, 12, 31)),
        ],
        days_current=365,
        days_prior=365,
        days_two_prior=365,
    )
    result = determine_residency(input_data)
    assert result.exempt_years_used == 5
    assert result.is_exempt_individual is False
    assert result.spt_weighted_days == pytest.approx(547.5)
    assert result.status == ResidencyStatus.RESIDENT_ALIEN
# 6. Exempt years exhausted + low presence -> stays NONRESIDENT_ALIEN
def test_exhausted_exempt_years_low_presence_stays_nonresident():
    input_data = make_input(
        tax_year=2025,
        entry_date=date(2020, 1, 1),
        visa_history=[
            VisaPeriod(visa_type=VisaType.F1, start_date=date(2020, 1, 1), end_date=date(2024, 12, 31)),
        ],
        days_current=20,
        days_prior=20,
        days_two_prior=20,
    )
    result = determine_residency(input_data)
    assert result.exempt_years_used == 5
    assert result.status == ResidencyStatus.NONRESIDENT_ALIEN
# 7. Pure H-1B, no F/J/M/Q history at all -> straight to SPT, no exemption
# (regression test for the H-1B exemption bug)
def test_pure_h1b_no_prior_student_status_skips_exemption():
    input_data = make_input(
        tax_year=2025,
        entry_date=date(2025, 1, 1),
        visa_history=[
            VisaPeriod(visa_type=VisaType.H1B, start_date=date(2025, 1, 1), end_date=None),
        ],
        days_current=184,
        days_prior=0,
        days_two_prior=0,
    )
    result = determine_residency(input_data)
    assert result.is_exempt_individual is False
    assert result.exempt_years_used == 0
    assert result.status == ResidencyStatus.RESIDENT_ALIEN
# 8. F-1 through June, H-1B from July on, same tax year -> DUAL_STATUS
# (regression test for the mid-year transition bug)
def test_mid_year_f1_to_h1b_transition_is_dual_status():
    input_data = make_input(
        tax_year=2025,
        entry_date=date(2021, 8, 8),
        visa_history=[
            VisaPeriod(visa_type=VisaType.F1, start_date=date(2021, 8, 8), end_date=date(2025, 6, 30)),
            VisaPeriod(visa_type=VisaType.H1B, start_date=date(2025, 7, 1), end_date=None),
        ],
        days_current=365,
        days_prior=365,
        days_two_prior=365,
    )
    result = determine_residency(input_data)
    assert result.status == ResidencyStatus.DUAL_STATUS
    assert result.spt_weighted_days == 0.0