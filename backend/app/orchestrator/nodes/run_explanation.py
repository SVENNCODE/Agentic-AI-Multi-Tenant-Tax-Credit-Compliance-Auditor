import logging
import time

from anthropic import APIConnectionError, APITimeoutError, RateLimitError, InternalServerError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from langchain_anthropic import ChatAnthropic

from app.agents.explanation_engine import (
    ExplanationReportOutput,
    SYSTEM_PROMPT,
    MANDATORY_DISCLAIMER,
    _build_facts_payload,
    _consolidate_next_steps,
    _clip,
    build_default_llm,
)
from app.orchestrator.state import AuditGraphState, StepStatus

logger = logging.getLogger(__name__)

TRANSIENT_ANTHROPIC_ERRORS = (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    InternalServerError,
)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(TRANSIENT_ANTHROPIC_ERRORS),
    reraise=True,
)
def _call_claude_with_retry(structured_llm, messages):
    """The only retried step — the network call itself. include_raw=True
    keeps both the parsed object and the raw AIMessage (which carries
    token usage) rather than discarding the raw response."""
    return structured_llm.invoke(messages)


def run_explanation(state: AuditGraphState, llm: ChatAnthropic | None = None) -> dict:
    """
    Node function: synthesize a human-readable report from the already-
    computed residency + credit results. Failure here is NOT treated as
    fatal to the whole pipeline — the deterministic results are still
    valid and should still be persisted even without an explanation.
    """
    if llm is None:
        llm = build_default_llm()

    structured_llm = llm.with_structured_output(ExplanationReportOutput, include_raw=True)

    facts = _build_facts_payload(state.residency_determination, state.credit_evaluations)

    start_time = time.time()

    try:
        response = _call_claude_with_retry(
            structured_llm,
            [
                ("system", SYSTEM_PROMPT),
                ("human", f"Here is the engine output to explain:\n\n{facts}"),
            ],
        )
    except Exception:
        logger.exception("Explanation synthesis stage failed")
        return {
            "errors": ["The explanation summary could not be generated. "
                       "Your results are still valid and will be saved "
                       "without a written summary."],
            "explanation_step_status": StepStatus.FAILED,
        }

    elapsed_ms = round((time.time() - start_time) * 1000, 2)

    if response.get("parsing_error"):
        logger.error(f"Structured output parsing failed: {response['parsing_error']}")
        return {
            "errors": ["The explanation summary could not be generated in "
                       "the expected format. Your results are still valid "
                       "and will be saved without a written summary."],
            "explanation_step_status": StepStatus.FAILED,
        }

    raw_message = response["raw"]
    parsed: ExplanationReportOutput = response["parsed"]

    status_by_rule_code = {r.rule_code: r.status for r in state.credit_evaluations}
    merged_credit_breakdown = []
    for item in parsed.credit_breakdown:
        real_status = status_by_rule_code.get(item.rule_code)
        if real_status is None:
            continue
        merged_credit_breakdown.append({
            "rule_code": item.rule_code,
            "status": real_status,
            "explanation": _clip(item.explanation),
        })

    report = {
        "executive_summary": _clip(parsed.executive_summary),
        "residency_breakdown": _clip(parsed.residency_breakdown),
        "credit_breakdown": merged_credit_breakdown,
        "next_steps": _consolidate_next_steps(
            parsed.next_steps,
            rule_codes=[r.rule_code for r in state.credit_evaluations],
        ),
        "disclaimer": MANDATORY_DISCLAIMER,
    }

    usage = getattr(raw_message, "usage_metadata", None) or {}

    updated_metadata = state.metadata.copy()
    updated_metadata.update({
        "llm_model": llm.model,
        "llm_input_tokens": usage.get("input_tokens"),
        "llm_output_tokens": usage.get("output_tokens"),
        "explanation_latency_ms": elapsed_ms,
    })

    return {
        "explanation_report": report,
        "explanation_step_status": StepStatus.COMPLETED,
        "metadata": updated_metadata,
    }