import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials
from supabase import create_client, Client, ClientOptions

from app.core.security import security, verify_supabase_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["Audit Summary"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# Explicit column lists never `select("*")` into an API response, so new
# internal columns (run_metadata, ids, user_id) are not leaked by default.
DETERMINATION_COLUMNS = (
    "tax_year,determined_residency,target_form,is_exempt_individual,"
    "exempt_years_used,audit_trail,explanation_report"
)
CREDIT_COLUMNS = (
    "source_type,federal_credit_code,nj_rule_code,treaty_country_code,"
    "status,reason,estimated_amount"
)


@router.get("/summary")
def get_audit_summary(
    tax_year: Optional[int] = Query(
        None, ge=2000, le=2100,
        description="Tax year to fetch. Defaults to the user's most recent.",
    ),
    user_payload: dict = Depends(verify_supabase_token),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Read-only. Uses the user-scoped client (RLS-enforced), never the
    service role, this route only ever needs to see the requesting
    user's own rows, and RLS already guarantees that at the database
    level rather than relying on this code to filter correctly.
    """
    user_id = user_payload["sub"]
    jwt_token = credentials.credentials

    user_client: Client = create_client(
        SUPABASE_URL,
        SUPABASE_ANON_KEY,
        options=ClientOptions(headers={"Authorization": f"Bearer {jwt_token}"}),
    )

    if tax_year is None:
        latest = (
            user_client.table("residency_determinations")
            .select("tax_year")
            .eq("user_id", user_id)
            .order("tax_year", desc=True)
            .limit(1)
            .execute()
        )
        if not latest.data:
            raise HTTPException(
                status_code=404,
                detail="No audit results found yet. Complete the questionnaire first.",
            )
        tax_year = latest.data[0]["tax_year"]

    try:
        det_response = (
            user_client.table("residency_determinations")
            .select(DETERMINATION_COLUMNS)
            .eq("user_id", user_id)
            .eq("tax_year", tax_year)
            .maybe_single()
            .execute()
        )
        determination_row = det_response.data if det_response else None
    except Exception:
        logger.exception("Fetching residency determination failed")
        raise HTTPException(status_code=500, detail="Could not load your results.")

    if determination_row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No audit results found for tax year {tax_year}.",
        )

    credits_response = (
        user_client.table("credit_evaluations")
        .select(CREDIT_COLUMNS)
        .eq("user_id", user_id)
        .eq("tax_year", tax_year)
        .execute()
    )
    credit_rows = credits_response.data or []

    eligible_count = sum(1 for c in credit_rows if c["status"] == "ELIGIBLE")
    needs_documentation_count = sum(
        1 for c in credit_rows if c["status"] == "NEEDS_DOCUMENTATION"
    )
    ineligible_count = sum(
        1 for c in credit_rows if c["status"] in ("INELIGIBLE", "NOT_APPLICABLE")
    )

    residency_determined = determination_row is not None
    credits_evaluated = len(credit_rows) > 0
    completed_signals = sum([residency_determined, credits_evaluated])
    readiness_percentage = round((completed_signals / 2) * 100)

    return {
        "tax_year": tax_year,
        "readiness_percentage": readiness_percentage,
        "readiness_note": (
            "Based on residency and credit evaluation only. Document "
            "upload tracking is not yet available."
        ),
        "residency": {
            "determined": residency_determined,
            "status": determination_row.get("determined_residency"),
            "target_form": determination_row.get("target_form"),
            "is_exempt_individual": determination_row.get("is_exempt_individual"),
            "exempt_years_used": determination_row.get("exempt_years_used"),
            "audit_trail": determination_row.get("audit_trail"),
        },
        "credits": {
            "evaluated": credits_evaluated,
            "total": len(credit_rows),
            "eligible_count": eligible_count,
            "needs_documentation_count": needs_documentation_count,
            "ineligible_count": ineligible_count,
            "items": credit_rows,
        },
        "documents": {
            "available": False,
            "note": "Document upload is not yet available.",
        },
        "explanation_report": determination_row.get("explanation_report"),
    }