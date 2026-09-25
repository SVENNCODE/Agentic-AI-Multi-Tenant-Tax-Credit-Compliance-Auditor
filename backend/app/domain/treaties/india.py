"""US-India Income Tax Treaty plugin (Article 21(2) student standard deduction).

Registered in app.domain.treaty_engine.TREATY_HANDLERS under "IND".
"""

from app.domain.schemas import (
    CreditEvaluationResult,
    QuestionnaireInput,
    ResidencyDetermination,
    ResidencyStatus,
    VisaType,
)

# 2025 federal standard deduction amounts, per IRS Rev. Proc. 2024-40 as
# amended by the One Big Beautiful Bill Act (July 2025). Same hardcoded-
# constant problem as SPT thresholds before spt_rules existed — this
# should eventually move to a versioned DB table keyed by (tax_year,
# filing_status), same pattern as spt_rules, so it doesn't need a code
# deploy every year and stays reproducible for past determinations.
STANDARD_DEDUCTION_2025 = {
    "SINGLE": 15750.0,
    "MARRIED_FILING_SEPARATELY": 15750.0,
    "HEAD_OF_HOUSEHOLD": 23625.0,
    "MARRIED_FILING_JOINTLY": 31500.0,
    "QUALIFYING_SURVIVING_SPOUSE": 31500.0,
}


COUNTRY_CODE = "IND"


def evaluate_india_treaty_benefit(
    residency: ResidencyDetermination,
    questionnaire: QuestionnaireInput,
) -> CreditEvaluationResult:
    """
    Evaluates US-India Income Tax Treaty Article 21(2) Standard Deduction
    eligibility. Pure domain logic: zero DB side-effects or network calls.
    """
    # 1. Citizenship Country Check
    if questionnaire.citizenship_country != COUNTRY_CODE:
        return CreditEvaluationResult(
            source_type="TREATY_BENEFIT",
            rule_code="US_IND_ART21_2",
            status="INELIGIBLE",
            reason=(
                "US-India Treaty Article 21(2) is exclusively restricted to "
                "citizens/nationals of India."
            ),
            estimated_amount=0.0,
            country_code=COUNTRY_CODE,
        )

    # 2. Visa Category Check (F-1, J-1 student categories)
    eligible_visas = {VisaType.F1, VisaType.J1}
    if questionnaire.current_visa_type not in eligible_visas:
        return CreditEvaluationResult(
            source_type="TREATY_BENEFIT",
            rule_code="US_IND_ART21_2",
            status="INELIGIBLE",
            reason="US-India Treaty Article 21(2) requires active F-1 or J-1 student/scholar status.",
            estimated_amount=0.0,
            country_code=COUNTRY_CODE,
        )
    # eligibility for a split nonresident/resident year is genuinely complex and this
    # tool doesn't model it. Check this BEFORE the RESIDENT_ALIEN branch
    # below, since a dual-status determination is neither RESIDENT_ALIEN
    # nor NONRESIDENT_ALIEN and shouldn't be caught by either.
    if residency.status == ResidencyStatus.DUAL_STATUS:
        return CreditEvaluationResult(
            source_type="TREATY_BENEFIT",
            rule_code="US_IND_ART21_2",
            status="NEEDS_DOCUMENTATION",
            reason=(
                "Taxpayer has a dual-status tax year. Treaty-based standard "
                "deduction eligibility for dual-status filers is complex — "
                "a tax professional should review this specific case rather "
                "than relying on an automated check."
            ),
            estimated_amount=0.0,
            country_code=COUNTRY_CODE,
        )
    # An UNDETERMINED residency means the inputs were ambiguous or
    # conflicting; treaty eligibility cannot be decided on top of that.
    if residency.status == ResidencyStatus.UNDETERMINED:
        return CreditEvaluationResult(
            source_type="TREATY_BENEFIT",
            rule_code="US_IND_ART21_2",
            status="NEEDS_DOCUMENTATION",
            reason=(
                "Residency status could not be determined from the answers "
                "provided, so treaty eligibility cannot be evaluated yet. "
                "Review your entry date and visa history."
            ),
            estimated_amount=None,
            country_code=COUNTRY_CODE,
        )
    # 3. Residency Status Check
    # Treaty standard deduction is only claimed on Form 1040-NR by
    # Nonresident Aliens. Once a student becomes a Resident Alien under
    # SPT, they already receive the full US Standard Deduction naturally.
    if residency.status == ResidencyStatus.RESIDENT_ALIEN:
        return CreditEvaluationResult(
            source_type="TREATY_BENEFIT",
            rule_code="US_IND_ART21_2",
            status="NOT_APPLICABLE",
            reason="Taxpayer is already classified as a Resident Alien for tax purposes and receives the standard deduction under standard IRC rules.",
            estimated_amount=0.0,
            country_code=COUNTRY_CODE,
        )

    # 4. Standard deduction amount, varies by filing status.
    # Falls back to the SINGLE amount if filing status isn't in the table
    # (shouldn't happen given Zod's enum validation, but avoids a KeyError
    # crash rather than silently guessing wrong).
    filing_status = getattr(questionnaire.filing_status, "value", questionnaire.filing_status)
    estimated_amount = STANDARD_DEDUCTION_2025.get(
        filing_status, STANDARD_DEDUCTION_2025["SINGLE"]
    )

    return CreditEvaluationResult(
        source_type="TREATY_BENEFIT",
        rule_code="US_IND_ART21_2",
        status="ELIGIBLE",
        reason=(
            "Eligible under US-India Tax Treaty Article 21(2) to claim the "
            f"full Federal Standard Deduction (${estimated_amount:,.2f} for "
            f"{filing_status}) on Form 1040-NR."
        ),
        estimated_amount=estimated_amount,
        country_code=COUNTRY_CODE,
    )