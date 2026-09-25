from datetime import date

from app.domain.schemas import (
    TaxPayerInput,
    ResidencyDetermination,
    ResidencyStatus,
    AuditTrailStep,
    VisaType,
)

EXEMPT_STUDENT_YEAR_LIMIT = 5

DEFAULT_MIN_CURRENT_YEAR_DAYS = 31
DEFAULT_SPT_THRESHOLD_DAYS = 183
DEFAULT_PRIOR_YEAR_WEIGHT = 1 / 3
DEFAULT_TWO_YEARS_PRIOR_WEIGHT = 1 / 6

STUDENT_VISAS = {VisaType.F1, VisaType.J1, VisaType.M1, VisaType.Q1}


def count_exempt_years(input_data: TaxPayerInput) -> int:
    """
    Counts calendar years (prior to tax_year) in which the taxpayer
    held student status (F, J, M, Q). Any presence in a calendar year counts
    as 1 year, per IRS Pub 519's lifetime, non-consecutive counting rule.
    """
    exempt_calendar_years = set()

    for period in input_data.visa_history:
        if period.visa_type in STUDENT_VISAS:
            start_year = period.start_date.year
            end_year = period.end_date.year if period.end_date else input_data.tax_year

            for y in range(start_year, min(end_year + 1, input_data.tax_year)):
                exempt_calendar_years.add(y)

    return len(exempt_calendar_years)


def holds_exempt_status_in_tax_year(input_data: TaxPayerInput) -> bool:
    """
    Whether the taxpayer held F/J/M/Q status at some point during the tax
    year being evaluated.
    """
    for period in input_data.visa_history:
        if period.visa_type not in STUDENT_VISAS:
            continue
        start_year = period.start_date.year
        end_year = period.end_date.year if period.end_date else input_data.tax_year
        if start_year <= input_data.tax_year <= end_year:
            return True

    return False


def has_mid_year_status_change(input_data: TaxPayerInput) -> bool:
    """
    Detects whether the taxpayer's exempt/non-exempt status actually changed
    *within* the tax year being evaluated like for example F-1 through June, H-1B from
    July on. This is a dual-status scenario: nonresident for the exempt
    portion, resident for the non-exempt portion, requiring a split-year
    calculation the current data model (one day-count total per year, not
    per period) can't represent correctly.
    """
    year_start = date(input_data.tax_year, 1, 1)
    year_end = date(input_data.tax_year, 12, 31)

    statuses_held_this_year: set[bool] = set()  # True = exempt, False = not

    for period in input_data.visa_history:
        period_start = period.start_date
        period_end = period.end_date or date(input_data.tax_year, 12, 31)

        if period_end < year_start or period_start > year_end:
            continue

        statuses_held_this_year.add(period.visa_type in STUDENT_VISAS)

    # If the taxpayer held both an exempt-type period and a non-exempt-type
    # period overlapping the same tax year, that's a mid-year change.
    return len(statuses_held_this_year) > 1


def find_ambiguities(input_data: TaxPayerInput) -> list[str]:
    """
    Returns a human-readable reasons why the inputs cannot support a reliable
    residency determination. An empty list means the inputs are usable.

    This is made conservative on purpose so each check represents data that is missing
    or self-contradictory, where forcing RESIDENT/NONRESIDENT would be a guess.
    """
    problems: list[str] = []
    tax_year = input_data.tax_year
    year_end = date(tax_year, 12, 31)

    if input_data.entry_date is None:
        problems.append("No U.S. entry date was provided.")
    elif input_data.entry_date > year_end:
        problems.append(
            f"The U.S. entry date ({input_data.entry_date.isoformat()}) is after "
            f"the end of tax year {tax_year}."
        )

    if not input_data.visa_history:
        problems.append("No visa status history was provided.")

    periods = sorted(input_data.visa_history, key=lambda p: p.start_date)
    for period in periods:
        if period.end_date is not None and period.end_date < period.start_date:
            problems.append(
                f"A {period.visa_type.value} period ends before it starts."
            )
        if (
            input_data.entry_date is not None
            and period.start_date < input_data.entry_date
            and period.visa_type != VisaType.NONE
        ):
            problems.append(
                f"A {period.visa_type.value} period starts "
                f"({period.start_date.isoformat()}) before the reported U.S. "
                f"entry date ({input_data.entry_date.isoformat()})."
            )

    # Overlapping periods with DIFFERENT visa types are contradictory: a
    # person holds one immigration status at a time. (Back-to-back periods
    # sharing a boundary day are allowed.)
    for i, a in enumerate(periods):
        a_end = a.end_date or year_end
        for b in periods[i + 1:]:
            if b.start_date >= a_end:
                continue
            if a.visa_type != b.visa_type:
                problems.append(
                    f"Visa periods overlap with conflicting types "
                    f"({a.visa_type.value} and {b.visa_type.value})."
                )

    return list(dict.fromkeys(problems))


def determine_residency(
    input_data: TaxPayerInput,
    min_current_year_days: int = DEFAULT_MIN_CURRENT_YEAR_DAYS,
    spt_threshold_days: int = DEFAULT_SPT_THRESHOLD_DAYS,
    prior_year_weight: float = DEFAULT_PRIOR_YEAR_WEIGHT,
    two_years_prior_weight: float = DEFAULT_TWO_YEARS_PRIOR_WEIGHT,
) -> ResidencyDetermination:
    audit_trail: list[AuditTrailStep] = []

    # -1. Ambiguity gate
    ambiguities = find_ambiguities(input_data)
    if ambiguities:
        audit_trail.append(AuditTrailStep(
            rule="Input Consistency Check",
            passed=False,
            details=(
                "Residency could not be determined because: "
                + " ".join(ambiguities)
                + " Correct these answers in the questionnaire, or have a tax "
                "professional review your situation."
            ),
        ))
        return ResidencyDetermination(
            status=ResidencyStatus.UNDETERMINED,
            is_exempt_individual=False,
            exempt_years_used=0,
            spt_weighted_days=0.0,
            target_form="Undetermined — review your answers or consult a tax professional",
            audit_trail=audit_trail,
        )

    # 0. Dual-status gate — 
    if has_mid_year_status_change(input_data):
        audit_trail.append(AuditTrailStep(
            rule="Dual-Status Year Detection",
            passed=False,
            details=(
                f"Taxpayer's visa status changed between exempt (F/J/M/Q) and "
                f"non-exempt status within {input_data.tax_year}. This is a "
                "dual-status tax year, which requires splitting the year into "
                "a nonresident period and a resident period. This cannot be "
                "determined automatically from a single annual day count — "
                "a tax professional should review dual-status filing "
                "requirements (Form 1040 and Form 1040-NR are both typically "
                "involved)."
            ),
        ))
        return ResidencyDetermination(
            status=ResidencyStatus.DUAL_STATUS,
            is_exempt_individual=False,
            exempt_years_used=count_exempt_years(input_data),
            spt_weighted_days=0.0,
            target_form="Dual-Status Return (1040 + 1040-NR) — consult a tax professional",
            audit_trail=audit_trail,
        )

    # 1. Evaluate Exempt Individual Status (F/J/M/Q Student 5-Year Rule)
    exempt_years = count_exempt_years(input_data)
    holds_exempt_status = holds_exempt_status_in_tax_year(input_data)

    if holds_exempt_status and exempt_years < EXEMPT_STUDENT_YEAR_LIMIT:
        audit_trail.append(AuditTrailStep(
            rule="F/J/M/Q Student Exempt Individual Rule (IRS Pub 519)",
            passed=True,
            details=(
                f"Taxpayer holds F/J/M/Q status in {input_data.tax_year} and has used "
                f"{exempt_years} of {EXEMPT_STUDENT_YEAR_LIMIT} exempt calendar years. "
                "Exempt from Substantial Presence Test."
            ),
        ))

        return ResidencyDetermination(
            status=ResidencyStatus.NONRESIDENT_ALIEN,
            is_exempt_individual=True,
            exempt_years_used=exempt_years,
            spt_weighted_days=0.0,
            target_form="Form 1040-NR",
            audit_trail=audit_trail,
        )

    # 2. Substantial Presence Test (SPT) fallback
    if not holds_exempt_status:
        audit_trail.append(AuditTrailStep(
            rule="F/J/M/Q Student Exempt Individual Rule",
            passed=False,
            details=(
                f"Taxpayer does not hold F/J/M/Q status in {input_data.tax_year}. "
                "Not eligible for the exempt individual rule this year — "
                "proceeding to Substantial Presence Test (SPT)."
            ),
        ))
    else:
        audit_trail.append(AuditTrailStep(
            rule="F/J/M/Q Student Exempt Individual Rule",
            passed=False,
            details=(
                f"Exempt years exhausted ({exempt_years} years used). "
                "Proceeding to Substantial Presence Test (SPT)."
            ),
        ))

    spt_days = (
        input_data.days_present_current_year
        + (input_data.days_present_prior_year * prior_year_weight)
        + (input_data.days_present_two_years_prior * two_years_prior_weight)
    )

    meets_min_day_rule = input_data.days_present_current_year >= min_current_year_days
    meets_weighted_rule = spt_days >= spt_threshold_days

    if meets_min_day_rule and meets_weighted_rule:
        audit_trail.append(AuditTrailStep(
            rule="Substantial Presence Test (SPT)",
            passed=True,
            details=(
                f"Meets SPT: {input_data.days_present_current_year} days in "
                f"{input_data.tax_year} (>= {min_current_year_days}) and "
                f"{spt_days:.1f} weighted days (>= {spt_threshold_days})."
            ),
        ))
        return ResidencyDetermination(
            status=ResidencyStatus.RESIDENT_ALIEN,
            is_exempt_individual=False,
            exempt_years_used=exempt_years,
            spt_weighted_days=spt_days,
            target_form="Form 1040",
            audit_trail=audit_trail,
        )

    audit_trail.append(AuditTrailStep(
        rule="Substantial Presence Test (SPT)",
        passed=False,
        details=f"Failed SPT: total weighted days = {spt_days:.1f} (< {spt_threshold_days}).",
    ))
    return ResidencyDetermination(
        status=ResidencyStatus.NONRESIDENT_ALIEN,
        is_exempt_individual=False,
        exempt_years_used=exempt_years,
        spt_weighted_days=spt_days,
        target_form="Form 1040-NR",
        audit_trail=audit_trail,
    )