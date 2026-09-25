from typing import Optional
from app.domain.schemas import (
    CreditEvaluationResult,
    QuestionnaireInput,
    ResidencyDetermination,
    ResidencyStatus,
)

def evaluate_nj_deductions(
    residency: ResidencyDetermination,
    questionnaire: QuestionnaireInput,
) -> list[CreditEvaluationResult]:
    results = []

    is_nj_resident = questionnaire.state_of_residence == "NJ"
    if not is_nj_resident:
        results.append(CreditEvaluationResult(
            source_type="NJ_DEDUCTION",
            rule_code="NJ_RESIDENCY_REQ",
            status="INELIGIBLE",
            reason="NJ state tax deductions require New Jersey residency during the tax year.",
            estimated_amount=0.0,
        ))
        return results

    # NJ College Affordability Act income cap
    if questionnaire.annual_income > 200000:
        results.append(CreditEvaluationResult(
            source_type="NJ_DEDUCTION",
            rule_code="NJ_TUITION_DEDUCTION",
            status="INELIGIBLE",
            reason="NJ College Affordability Act deductions require NJ gross income of $200,000 or less.",
            estimated_amount=0.0,
        ))
        return results

    if questionnaire.tuition_paid > 0 and questionnaire.is_fulltime_student:
        if questionnaire.tuition_paid_to_nj is False:
            results.append(CreditEvaluationResult(
                source_type="NJ_DEDUCTION",
                rule_code="NJ_TUITION_DEDUCTION",
                status="INELIGIBLE",
                reason="The NJ College Tuition Deduction only applies to tuition paid to an in-State (New Jersey) institution.",
                estimated_amount=0.0,
            ))
        elif questionnaire.tuition_paid_to_nj is None:
            results.append(CreditEvaluationResult(
                source_type="NJ_DEDUCTION",
                rule_code="NJ_TUITION_DEDUCTION",
                status="NEEDS_DOCUMENTATION",
                reason="Confirm whether tuition was paid to a New Jersey institution before this deduction can be evaluated.",
                estimated_amount=None,
            ))
        elif residency.status == ResidencyStatus.UNDETERMINED:
            results.append(CreditEvaluationResult(
                source_type="NJ_DEDUCTION",
                rule_code="NJ_TUITION_DEDUCTION",
                status="NEEDS_DOCUMENTATION",
                reason="Federal residency status could not be determined from the answers provided, so the NJ return type (NJ-1040 vs NJ-1040NR) and this deduction cannot be evaluated yet.",
                estimated_amount=None,
            ))
        elif residency.status == ResidencyStatus.NONRESIDENT_ALIEN:
            results.append(CreditEvaluationResult(
                source_type="NJ_DEDUCTION",
                rule_code="NJ_TUITION_DEDUCTION",
                status="NEEDS_DOCUMENTATION",
                reason="Federal Nonresident Aliens filing Form 1040-NR must verify if they file NJ-1040NR vs NJ-1040 resident return before claiming college tuition deduction.",
                estimated_amount=None,
            ))
        else:
            expenses_used = min(questionnaire.tuition_paid, 10000.0)
            results.append(CreditEvaluationResult(
                source_type="NJ_DEDUCTION",
                rule_code="NJ_TUITION_DEDUCTION",
                status="ELIGIBLE",
                reason="Eligible for NJ College Tuition Deduction (up to $10,000 for full-time enrollment at a New Jersey institution).",
                estimated_amount=expenses_used,
            ))
    else:
        results.append(CreditEvaluationResult(
            source_type="NJ_DEDUCTION",
            rule_code="NJ_TUITION_DEDUCTION",
            status="INELIGIBLE",
            reason="Requires full-time enrollment and eligible tuition payments to an NJ institution.",
            estimated_amount=0.0,
        ))

    return results