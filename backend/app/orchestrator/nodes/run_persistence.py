import logging
from tenacity import retry, stop_after_attempt, wait_exponential

from app.orchestrator.state import AuditGraphState, StepStatus

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _write_credit_evaluations_with_retry(service_client, user_id: str, tax_year: int, rows: list[dict]):
    """
    Atomically replaces every credit_evaluations row for (user_id, tax_year)
    via the replace_credit_evaluations Postgres function
    (supabase/migrations/*_atomic_replace_rpcs.sql).

    The DELETE and INSERT run inside ONE function call, and a Postgres
    function always executes inside a single transaction: if the INSERT
    fails, the DELETE is rolled back with it. The previous client-side
    delete-then-insert could leave a user with zero credit rows if the
    insert failed after the delete succeeded.

    Idempotent, so the tenacity retry is safe: a retried call simply
    replaces the rows again with identical data.
    """
    service_client.rpc(
        "replace_credit_evaluations",
        {"p_user_id": user_id, "p_tax_year": tax_year, "p_rows": rows},
    ).execute()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _update_residency_determination_with_retry(
    service_client, determination_id: str, explanation_report, run_metadata: dict
):
    """
    Targeted UPDATE by id, not a full upsert — the row already exists from
    run_residency's earlier write; this only attaches the explanation and
    metadata that weren't available yet at that point. Idempotent: setting
    the same two columns to the same values twice is a no-op, safe to
    retry.
    """
    service_client.table("residency_determinations").update({
        "explanation_report": explanation_report,
        "run_metadata": run_metadata,
    }).eq("id", determination_id).execute()


def run_persistence(state: AuditGraphState, service_client) -> dict:
    """
    Final node: write credit_evaluations, and attach the explanation
    report + run metadata to the already-persisted residency_determinations
    row. Runs regardless of whether run_explanation succeeded — an absent
    explanation_report (None) is a valid, expected state, not an error
    condition here.
    """
    errors = []

    try:
        credit_evaluation_rows = [
            {
                "user_id": state.user_id,
                "tax_year": state.tax_year,
                "source_type": result.source_type,
                "federal_credit_code": result.rule_code if result.source_type == "FEDERAL_CREDIT" else None,
                "nj_rule_code": result.rule_code if result.source_type == "NJ_DEDUCTION" else None,
                "treaty_country_code": result.country_code if result.source_type == "TREATY_BENEFIT" else None,
                "status": result.status,
                "reason": result.reason,
                "estimated_amount": result.estimated_amount,
                "based_on_residency_determination_id": state.residency_determination_id,
            }
            for result in state.credit_evaluations
        ]

        _write_credit_evaluations_with_retry(
            service_client, state.user_id, state.tax_year, credit_evaluation_rows
        )

    except Exception:
        logger.exception("Persisting credit_evaluations failed")
        errors.append("Your credit and deduction results could not be saved. "
                       "This has been logged for review.")

    try:
        if state.residency_determination_id:
            explanation_payload = (
                state.explanation_report.model_dump()
                if state.explanation_report is not None
                else None
            )
            _update_residency_determination_with_retry(
                service_client,
                state.residency_determination_id,
                explanation_payload,
                state.metadata,
            )
    except Exception:
        logger.exception("Attaching explanation_report/run_metadata failed")
        errors.append("Your summary explanation could not be saved, though "
                       "your underlying results are safe.")

    if errors:
        return {
            "errors": errors,
            "persistence_step_status": StepStatus.FAILED,
            "is_complete": True,
        }

    return {
        "persisted": True,
        "persistence_step_status": StepStatus.COMPLETED,
        "is_complete": True,
    }