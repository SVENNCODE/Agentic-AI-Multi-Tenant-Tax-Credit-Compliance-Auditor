import logging
from datetime import datetime, timezone

from app.domain.schemas import TaxPayerInput, VisaPeriod
from app.domain.calculator import determine_residency
from app.orchestrator.state import AuditGraphState, StepStatus
from app.data_access.rules_fetch import fetch_spt_rules

logger = logging.getLogger(__name__)


def _build_tax_payer_input(state: AuditGraphState) -> TaxPayerInput:
    q = state.questionnaire
    return TaxPayerInput(
        tax_year=q.tax_year,
        citizenship_country=q.citizenship_country,
        entry_date=q.us_entry_date,
        days_present_current_year=q.days_present_current_year,
        days_present_prior_year=q.days_present_prior_year,
        days_present_two_years_prior=q.days_present_two_years_prior,
        visa_history=[
            VisaPeriod(
                visa_type=period.visa_type,
                start_date=period.start_date,
                end_date=period.end_date or None,
            )
            for period in q.visa_status_periods
        ],
    )


def _write_residency_determination(service_client, row: dict) -> str:
    """Idempotent upsert on (user_id, tax_year). Retry already lives on
    fetch_spt_rules; this write is a single fast Postgres upsert and isn't
    separately wrapped — add a retry decorator here too if you start
    seeing transient write failures in practice."""
    response = (
        service_client.table("residency_determinations")
        .upsert(row, on_conflict="user_id,tax_year")
        .execute()
    )
    if not response.data:
        raise ValueError(
            f"Failed to retrieve upserted residency determination for user {row.get('user_id')}"
        )
    return response.data[0]["id"]


def run_residency(state: AuditGraphState, service_client) -> dict:
    """
    Fetch SPT thresholds (retriable I/O, inside fetch_spt_rules) -> compute
    (pure, never retried) -> persist immediately (this is the foundational
    compliance record, written before credit evaluation even begins, per
    the agreed hybrid persistence design).
    """
    try:
        spt_rules = fetch_spt_rules(service_client, state.tax_year)
        tax_payer_input = _build_tax_payer_input(state)

        determination = determine_residency(
            tax_payer_input,
            min_current_year_days=spt_rules.min_current_year_days,
            spt_threshold_days=spt_rules.spt_threshold_days,
            prior_year_weight=spt_rules.prior_year_weight,
            two_years_prior_weight=spt_rules.two_years_prior_weight,
        )

        determination_row = {
            "user_id": state.user_id,
            "tax_year": state.tax_year,
            "days_present_current_year": tax_payer_input.days_present_current_year,
            "days_present_prev_year1": tax_payer_input.days_present_prior_year,
            "days_present_prev_year2": tax_payer_input.days_present_two_years_prior,
            "spt_weighted_days": determination.spt_weighted_days,
            "is_exempt_individual": determination.is_exempt_individual,
            "exempt_years_used": determination.exempt_years_used,
            "determined_residency": determination.status.value,
            "target_form": determination.target_form,
            "applied_treaty_code": determination.applied_treaty_code,
            "audit_trail": [step.model_dump() for step in determination.audit_trail],
            "determined_at": datetime.now(timezone.utc).isoformat(),
        }

        determination_id = _write_residency_determination(service_client, determination_row)

        return {
            "residency_determination": determination,
            "residency_determination_id": determination_id,
            "residency_step_status": StepStatus.COMPLETED,
        }

    except Exception:
        logger.exception("Residency determination stage failed")
        return {
            "errors": ["Residency determination could not be completed. "
                       "This has been logged for review."],
            "residency_step_status": StepStatus.FAILED,
        }