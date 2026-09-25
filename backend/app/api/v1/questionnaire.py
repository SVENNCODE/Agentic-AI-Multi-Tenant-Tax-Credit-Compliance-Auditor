import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from supabase import Client, ClientOptions, create_client

from app.core.rate_limit import QUESTIONNAIRE_RATE_LIMIT, limiter
from app.core.security import security, verify_supabase_token
from app.domain.schemas import QuestionnaireInput
from app.orchestrator.audit_graph import build_audit_graph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/questionnaire", tags=["Questionnaire"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is not set")
if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL is not set")
if not SUPABASE_ANON_KEY:
    raise RuntimeError("SUPABASE_ANON_KEY is not set")

service_client: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Built ONCE at module load, the compiled graph is a static execution
# plan shared across every request. Only the STATE differs per request.
audit_graph = build_audit_graph(service_client)


@router.post("/save")
@limiter.limit(QUESTIONNAIRE_RATE_LIMIT)
def save_questionnaire_response(
    request: Request,
    response: Response,
    input_data: QuestionnaireInput,
    user_payload: dict = Depends(verify_supabase_token),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Plain `def`, not `async def` done on purpose. audit_graph.invoke() is
    blocking (Supabase I/O + a synchronous Claude call), so FastAPI runs this
    in its thread pool instead of blocking the event loop.

    Rate limited per authenticated user
    """
    user_id = user_payload["sub"]

    user_client: Client = create_client(
        SUPABASE_URL,
        SUPABASE_ANON_KEY,
        options=ClientOptions(
            headers={"Authorization": f"Bearer {credentials.credentials}"}
        ),
    )

    try:
        questionnaire_row = {
            "user_id": user_id,
            "tax_year": input_data.tax_year,
            "state_of_residence": input_data.state_of_residence,
            "filing_status": input_data.filing_status.value,
            "employment_type": input_data.employment_type.value,
            "is_fulltime_student": input_data.is_fulltime_student,
            "annual_income": input_data.annual_income,
            "number_of_employers": input_data.number_of_employers,
            "scholarship_amount": input_data.scholarship_amount,
            "tuition_paid": input_data.tuition_paid,
            "has_education_expenses": input_data.has_education_expenses,
            "has_childcare_expenses": input_data.has_childcare_expenses,
            "has_medical_expenses": input_data.has_medical_expenses,
            "has_charitable_donations": input_data.has_charitable_donations,
            "has_retirement_contributions": input_data.has_retirement_contributions,
            "raw_responses": input_data.model_dump(mode="json"),
            "is_completed": True,
        }
        user_client.table("questionnaire_responses").upsert(
            questionnaire_row, on_conflict="user_id,tax_year"
        ).execute()

        user_client.table("profiles").update(
            {
                "citizenship_country": input_data.citizenship_country,
                "us_entry_date": input_data.us_entry_date.isoformat(),
                "current_visa_type": input_data.current_visa_type.value,
            }
        ).eq("user_id", user_id).execute()

        # Atomic delete + re-insert inside one Postgres function
        # (supabase/migrations/*_atomic_replace_rpcs.sql). Runs as the
        # calling user (SECURITY INVOKER) and derives user_id from auth.uid(),
        # so RLS still applies and the client cannot target another user.
        period_rows = [
            {
                "visa_type": period.visa_type.value,
                "start_date": period.start_date.isoformat(),
                "end_date": period.end_date.isoformat() if period.end_date else None,
                "is_exempt_status": period.is_exempt_status,
            }
            for period in input_data.visa_status_periods
        ]
        user_client.rpc(
            "replace_visa_status_periods", {"p_periods": period_rows}
        ).execute()

    except Exception:
        logger.exception("Saving questionnaire inputs failed for user %s", user_id)
        raise HTTPException(
            status_code=500,
            detail="Failed to save your questionnaire. Please try again.",
        )

    initial_state = {
        "user_id": user_id,
        "tax_year": input_data.tax_year,
        "questionnaire": input_data,
        "errors": [],
        "metadata": {},
    }

    try:
        result = audit_graph.invoke(initial_state)
    except Exception:
        logger.exception("Audit graph execution failed unexpectedly")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing your submission.",
        )

    # is_complete is only set True inside run_persistence if the graph
    # exited early like (residency or credits FAILED)
    if not result.get("is_complete"):
        errors = result.get("errors") or ["Processing could not be completed."]
        raise HTTPException(status_code=500, detail=" ".join(errors))

    residency_determination = result.get("residency_determination")
    credit_evaluations = result.get("credit_evaluations", [])
    errors = result.get("errors", [])

    return {
        "status": "success" if not errors else "partial_success",
        "residency_determination_id": result.get("residency_determination_id"),
        "residency": residency_determination.model_dump() if residency_determination else None,
        "credit_evaluations": [c.model_dump() for c in credit_evaluations],
        "explanation_report": result.get("explanation_report"),
        "errors": errors,
    }
