import logging

from app.domain.credit_engine import evaluate_education_credit
from app.domain.nj_engine import evaluate_nj_deductions
from app.domain.treaty_engine import evaluate_treaty_benefit
from app.orchestrator.state import AuditGraphState, StepStatus
from app.data_access.rules_fetch import fetch_federal_credit_rules

logger = logging.getLogger(__name__)


def run_credits(state: AuditGraphState, service_client) -> dict:
    """
    Fetch federal credit rules (retriable I/O, inside
    fetch_federal_credit_rules) -> run all three evaluators (pure
    computation, never retried) against the already-computed residency
    determination.
    """
    if state.residency_determination is None:
        logger.error("run_credits called with no residency_determination in state")
        return {
            "errors": ["Credit evaluation could not run: no residency "
                       "determination was available."],
            "credit_evaluation_step_status": StepStatus.FAILED,
        }

    try:
        federal_rules = fetch_federal_credit_rules(service_client, state.tax_year)

        results = []

        for rule in federal_rules:
            results.append(
                evaluate_education_credit(
                    rule, state.residency_determination, state.questionnaire
                )
            )

        results.extend(
            evaluate_nj_deductions(state.residency_determination, state.questionnaire)
        )

        results.append(
            evaluate_treaty_benefit(state.residency_determination, state.questionnaire)
        )

        return {
            "credit_evaluations": results,
            "credit_evaluation_step_status": StepStatus.COMPLETED,
        }

    except Exception:
        logger.exception("Credit evaluation stage failed")
        return {
            "errors": ["Credit and deduction evaluation could not be "
                       "completed. This has been logged for review."],
            "credit_evaluation_step_status": StepStatus.FAILED,
        }