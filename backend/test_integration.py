"""
End-to-end integration test for build_audit_graph().

Uses REAL Supabase writes and a REAL Claude call and writes real rows to
your database, same category as test_explanation_node.py.
"""
from dotenv import load_dotenv
load_dotenv()

import os
from supabase import create_client # type: ignore

from app.domain.schemas import QuestionnaireInput, VisaStatusPeriodInput, VisaType
from app.orchestrator.audit_graph import build_audit_graph

TEST_USER_ID = os.getenv("TEST_USER_ID")
if not TEST_USER_ID:
    raise RuntimeError("Set TEST_USER_ID in backend/.env to a DEDICATED test account's id.")
TEST_TAX_YEAR = 2025

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

service_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def build_known_good_scenario() -> QuestionnaireInput:
    return QuestionnaireInput(
        tax_year=TEST_TAX_YEAR,
        state_of_residence="NJ",
        filing_status="SINGLE",
        citizenship_country="IND",
        us_entry_date="2020-01-01",
        current_visa_type=VisaType.F1,
        is_fulltime_student=True,
        employment_type="W2",
        spouse_is_us_citizen_or_resident=None,
        visa_status_periods=[
            VisaStatusPeriodInput(
                visa_type=VisaType.F1,
                start_date="2020-01-01",
                end_date="2024-12-31",
                is_exempt_status=True,
            )
        ],
        days_present_current_year=365,
        days_present_prior_year=365,
        days_present_two_years_prior=365,
        annual_income=45000.0,
        number_of_employers=1,
        scholarship_amount=2000.0,
        tuition_paid=7000.0,
        tuition_paid_to_nj_institution=True,
        has_education_expenses=True,
        has_childcare_expenses=False,
        has_medical_expenses=False,
        has_charitable_donations=False,
        has_retirement_contributions=False,
        has_valid_ssn=True,
        prior_years_aotc_claimed=0,
    )


def build_initial_state(questionnaire: QuestionnaireInput) -> dict:
    return {
        "user_id": TEST_USER_ID,
        "tax_year": TEST_TAX_YEAR,
        "questionnaire": questionnaire,
        "errors": [],
        "metadata": {},
    }


class _FailingStructuredLLM:
    def invoke(self, messages):
        raise RuntimeError("Simulated LLM failure for integration testing")


class _FailingLLM:
    """A fake LLM that always fails used to prove run_explanation's
    failure does NOT block run_persistence, without needing a real
    Anthropic outage to test it."""
    model = "fake-model-for-test"

    def with_structured_output(self, schema, include_raw=False):
        return _FailingStructuredLLM()


def verify_db_state(expect_explanation: bool):
    """Queries the DB directly, the real proof that persistence actually
    happened"""
    det_response = (
        service_client.table("residency_determinations")
        .select("*")
        .eq("user_id", TEST_USER_ID)
        .eq("tax_year", TEST_TAX_YEAR)
        .single()
        .execute()
    )
    det_row = det_response.data
    assert det_row is not None, "No residency_determinations row found in DB"
    assert det_row["determined_residency"] == "RESIDENT_ALIEN", \
        f"Expected RESIDENT_ALIEN, got {det_row['determined_residency']}"

    if expect_explanation:
        assert det_row["explanation_report"] is not None, \
            "Expected explanation_report to be populated, got None"
    else:
        assert det_row["explanation_report"] is None, \
            "Expected explanation_report to be None after simulated LLM failure"

    credits_response = (
        service_client.table("credit_evaluations")
        .select("*")
        .eq("user_id", TEST_USER_ID)
        .eq("tax_year", TEST_TAX_YEAR)
        .execute()
    )
    credit_rows = credits_response.data
    assert len(credit_rows) > 0, "No credit_evaluations rows found in DB"

    print(f"  DB check: residency row found, status={det_row['determined_residency']}")
    print(f"  DB check: {len(credit_rows)} credit_evaluations rows found")
    print(f"  DB check: explanation_report populated = {det_row['explanation_report'] is not None}")


def run_happy_path():
    print("=" * 70)
    print("TEST 1: Full happy path (real Claude call, real DB writes)")
    print("=" * 70)

    questionnaire = build_known_good_scenario()
    graph = build_audit_graph(service_client)
    result = graph.invoke(build_initial_state(questionnaire))

    assert result["residency_step_status"] == "COMPLETED", result["errors"]
    assert result["credit_evaluation_step_status"] == "COMPLETED", result["errors"]
    assert result["explanation_step_status"] == "COMPLETED", result["errors"]
    assert result["persistence_step_status"] == "COMPLETED", result["errors"]
    assert result["is_complete"] is True
    assert result["errors"] == [], f"Expected no errors, got: {result['errors']}"

    print("  In-memory state: all stages COMPLETED, no errors.")
    verify_db_state(expect_explanation=True)
    print("PASSED\n")


def run_explanation_failure_path():
    print("=" * 70)
    print("TEST 2: Explanation node fails -> persistence should STILL happen")
    print("=" * 70)

    questionnaire = build_known_good_scenario()
    graph = build_audit_graph(service_client, llm=_FailingLLM())

    result = graph.invoke(build_initial_state(questionnaire))

    assert result["residency_step_status"] == "COMPLETED", result["errors"]
    assert result["credit_evaluation_step_status"] == "COMPLETED", result["errors"]
    assert result["explanation_step_status"] == "FAILED", \
        "Expected explanation_step_status to be FAILED with the broken LLM"
    assert result["persistence_step_status"] == "COMPLETED", \
        "CRITICAL: persistence did not run after explanation failure — " \
        "the non-fatal-explanation-failure design is broken"
    assert result["is_complete"] is True
    assert len(result["errors"]) > 0, "Expected an error recorded for the explanation failure"

    print(f"  In-memory state: explanation FAILED (as expected), "
          f"persistence COMPLETED anyway.")
    print(f"  Recorded errors: {result['errors']}")
    verify_db_state(expect_explanation=False)
    print("PASSED\n")


if __name__ == "__main__":
    run_happy_path()
    run_explanation_failure_path()
    print("=" * 70)
    print("ALL INTEGRATION TESTS PASSED")
    print("=" * 70)