from typing import Optional
from pydantic import BaseModel

from app.domain.schemas import (
    FederalCreditRule,
    CreditEvaluationResult,
    ResidencyDetermination,
    ResidencyStatus,
    QuestionnaireInput,
)

MARRIED_FILING_SEPARATELY = "MARRIED_FILING_SEPARATELY"
MARRIED_FILING_JOINTLY = "MARRIED_FILING_JOINTLY"


def _is_nra_eligible_via_joint_election(
    residency: ResidencyDetermination,
    questionnaire: QuestionnaireInput,
) -> bool:
    """
    An NRA can only become eligible for these credits by electing to be
    treated as a resident for the full year under IRC 6013(g)/(h) which
    requires filing jointly with a US citizen/resident spouse. We don't
    model the election itself it is flagged as its own "consult a professional"
    case, but we can at least recognize when it's possible rather than just ruling it out.
    """
    return (
        questionnaire.filing_status == MARRIED_FILING_JOINTLY
        and questionnaire.spouse_is_us_citizen_or_resident is True
    )


def _magi_phaseout_fraction(
    magi: float, phaseout_start: float, phaseout_end: float
) -> float:
    """Returns the fraction of the credit that survives the phaseout.
    1.0 = full credit, 0.0 = fully phased out."""
    if magi <= phaseout_start:
        return 1.0
    if magi >= phaseout_end:
        return 0.0
    return 1.0 - ((magi - phaseout_start) / (phaseout_end - phaseout_start))

def evaluate_education_credit(
    rule: FederalCreditRule,
    residency: ResidencyDetermination,
    questionnaire: QuestionnaireInput,
) -> CreditEvaluationResult:
    """
    Evaluates a single federal education credit (AOTC or LLC) against a
    taxpayer's residency determination and questionnaire answers.

    Made conservative on purpose any input this function can't actually
    verify (SSN possession, prior years claimed, exact MAGI, precise
    enrollment status) returns NEEDS_DOCUMENTATION
    """

    # 0. Married filing separately disqualifies both AOTC and LLC entirely.
    if questionnaire.filing_status == MARRIED_FILING_SEPARATELY:
        return CreditEvaluationResult(
            source_type="FEDERAL_CREDIT",
            rule_code=rule.credit_code,
            status="INELIGIBLE",
            reason=(
                f"{rule.credit_name} cannot be claimed under "
                "Married Filing Separately status, regardless of income or "
                "residency."
            ),
        )

    # 1. Residency gate —
    if residency.status == ResidencyStatus.NONRESIDENT_ALIEN:
        if rule.allows_nonresident_aliens:
            pass  # not currently true for AOTC/LLC, but keeps this general
        elif _is_nra_eligible_via_joint_election(residency, questionnaire):
            return CreditEvaluationResult(
                source_type="FEDERAL_CREDIT",
                rule_code=rule.credit_code,
                status="NEEDS_DOCUMENTATION",
                reason=(
                    f"Taxpayer is a nonresident alien, but filing jointly "
                    "with a U.S. citizen/resident spouse may allow "
                    f"eligibility for {rule.credit_name} via a IRC 6013(g)/"
                    "(h) election to be treated as a resident for the full "
                    "year. This is a significant, largely irreversible "
                    "election a tax professional should be consulted "
                    "before proceeding."
                ),
            )
        else:
            return CreditEvaluationResult(
                source_type="FEDERAL_CREDIT",
                rule_code=rule.credit_code,
                status="INELIGIBLE",
                reason=(
                    f"{rule.credit_name} is not available to nonresident "
                    "aliens (IRC 25A(g)(7)). This is the taxpayer's current "
                    "federal residency status based on the Substantial "
                    "Presence Test / exempt-individual determination."
                ),
            )

    if residency.status == ResidencyStatus.UNDETERMINED:
        return CreditEvaluationResult(
            source_type="FEDERAL_CREDIT",
            rule_code=rule.credit_code,
            status="NEEDS_DOCUMENTATION",
            reason=(
                f"{rule.credit_name} eligibility depends on residency status, "
                "which could not be determined from the answers provided. "
                "Review your entry date and visa history first."
            ),
        )

    if residency.status == ResidencyStatus.DUAL_STATUS:
        return CreditEvaluationResult(
            source_type="FEDERAL_CREDIT",
            rule_code=rule.credit_code,
            status="NEEDS_DOCUMENTATION",
            reason=(
                "Taxpayer has a dual-status tax year. Education credit "
                "eligibility for dual-status filers is complex and "
                "generally limited a tax professional should review this "
                "specific case rather than relying on an automated check."
            ),
        )

    # From here on, residency.status == RESIDENT_ALIEN.
    if not questionnaire.has_education_expenses or questionnaire.tuition_paid <= 0:
        return CreditEvaluationResult(
            source_type="FEDERAL_CREDIT",
            rule_code=rule.credit_code,
            status="INELIGIBLE",
            reason=f"No tuition or education expenses reported for {rule.credit_name}.",
        )

    # 3. SSN requirement
    if rule.requires_ssn:
        if questionnaire.has_valid_ssn is False:
            return CreditEvaluationResult(
                source_type="FEDERAL_CREDIT",
                rule_code=rule.credit_code,
                status="INELIGIBLE",
                reason=(
                    f"{rule.credit_name} requires a valid SSN issued by the "
                    "return due date (an ITIN does not qualify)."
                ),
            )
        elif questionnaire.has_valid_ssn is None:
            return CreditEvaluationResult(
                source_type="FEDERAL_CREDIT",
                rule_code=rule.credit_code,
                status="NEEDS_DOCUMENTATION",
                reason=(
                    f"{rule.credit_name} requires a valid SSN (not an ITIN) "
                    "issued by the return due date. Confirm SSN status before "
                    "this credit can be marked eligible."
                ),
            )
    # has_valid_ssn is True -> falls through to the remaining checks below

    # 4. MAGI phaseout — using annual_income as an approximation of MAGI,
    if questionnaire.filing_status == MARRIED_FILING_JOINTLY:
        phaseout_start = rule.magi_phaseout_mfj_start
        phaseout_end = rule.magi_phaseout_mfj_end
    else:
        phaseout_start = rule.magi_phaseout_single_start
        phaseout_end = rule.magi_phaseout_single_end

    phaseout_fraction = _magi_phaseout_fraction(
        questionnaire.annual_income, phaseout_start, phaseout_end
    )

    if phaseout_fraction <= 0.0:
        return CreditEvaluationResult(
            source_type="FEDERAL_CREDIT",
            rule_code=rule.credit_code,
            status="INELIGIBLE",
            reason=(
                f"Reported income (${questionnaire.annual_income:,.2f}, used "
                "as an approximation of MAGI) exceeds the phaseout limit "
                f"(${phaseout_end:,.2f}) for {rule.credit_name}."
            ),
        )

    # 5. Enrollment status / years-claimed.
    if rule.min_enrollment_status == "half_time" and not questionnaire.is_fulltime_student:
        return CreditEvaluationResult(
            source_type="FEDERAL_CREDIT",
            rule_code=rule.credit_code,
            status="NEEDS_DOCUMENTATION",
            reason=(
                f"{rule.credit_name} requires at least half-time enrollment. "
                "Taxpayer did not indicate full-time student status,"
                "confirm actual enrollment status before finalizing."
            ),
        )

    if rule.max_years_claimable is not None:
        if questionnaire.prior_years_aotc_claimed is None:
            return CreditEvaluationResult(
                source_type="FEDERAL_CREDIT",
                rule_code=rule.credit_code,
                status="NEEDS_DOCUMENTATION",
                reason=(
                    f"{rule.credit_name} has a {rule.max_years_claimable}-year "
                    "lifetime limit. Confirm how many prior tax years this "
                    "credit has already been claimed before finalizing."
                ),
            )
        elif questionnaire.prior_years_aotc_claimed >= rule.max_years_claimable:
            return CreditEvaluationResult(
                source_type="FEDERAL_CREDIT",
                rule_code=rule.credit_code,
                status="INELIGIBLE",
                reason=(
                    f"{rule.credit_name} has already been claimed "
                    f"{questionnaire.prior_years_aotc_claimed} times, "
                    f"reaching its {rule.max_years_claimable}-year lifetime limit."
                ),
            )
        # else: fewer than max_years_claimable used -> falls through below

    # All checks passed with no unresolved data gaps.
    expenses_used = min(questionnaire.tuition_paid, rule.expense_cap)
    raw_credit = min(
        rule.max_credit_amount,
        expenses_used * (rule.max_credit_amount / rule.expense_cap),
    )
    estimated_amount = round(raw_credit * phaseout_fraction, 2)

    return CreditEvaluationResult(
        source_type="FEDERAL_CREDIT",
        rule_code=rule.credit_code,
        status="ELIGIBLE",
        reason=(
            "Resident alien with reported education expenses, income "
            "within the phaseout range, and no disqualifying factors found. "
            "Estimated amount is approximate, confirm exact figures with an "
            "actual tax software or a preparer."
        ),
        estimated_amount=estimated_amount,
    )