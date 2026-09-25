"""
Test script for generate_explanation_report(). Makes a REAL Anthropic API
call
"""

from app.domain.schemas import (
    ResidencyDetermination,
    ResidencyStatus,
    AuditTrailStep,
    CreditEvaluationResult,
)
from app.agents.explanation_engine import (
    generate_explanation_report,
    MANDATORY_DISCLAIMER,
)


def build_scenario():
    """NRA, filing jointly with a US citizen/resident spouse, AOTC and
    LLC both land on NEEDS_DOCUMENTATION via the IRC 6013(g)/(h) joint
    election path. This is a deliberately tricky case for the LLM to
    explain correctly without accidentally implying eligibility."""

    residency = ResidencyDetermination(
        status=ResidencyStatus.NONRESIDENT_ALIEN,
        is_exempt_individual=True,
        exempt_years_used=2,
        spt_weighted_days=0.0,
        target_form="Form 1040-NR",
        applied_treaty_code=None,
        audit_trail=[
            AuditTrailStep(
                rule="F/J/M/Q Student Exempt Individual Rule (IRS Pub 519)",
                passed=True,
                details="Taxpayer holds F/J/M/Q status in 2025 and has used "
                        "2 of 5 exempt calendar years. Exempt from "
                        "Substantial Presence Test.",
            )
        ],
    )

    credit_evaluations = [
        CreditEvaluationResult(
            source_type="FEDERAL_CREDIT",
            rule_code="AOTC",
            status="NEEDS_DOCUMENTATION",
            reason=(
                "Taxpayer is a nonresident alien, but filing jointly with a "
                "U.S. citizen/resident spouse may allow eligibility for "
                "American Opportunity Tax Credit via a IRC 6013(g)/(h) "
                "election to be treated as a resident for the full year. "
                "This is a significant, largely irreversible election a "
                "tax professional should be consulted before proceeding, "
                "not decided automatically here."
            ),
            estimated_amount=None,
        ),
        CreditEvaluationResult(
            source_type="FEDERAL_CREDIT",
            rule_code="LLC",
            status="NEEDS_DOCUMENTATION",
            reason=(
                "Taxpayer is a nonresident alien, but filing jointly with a "
                "U.S. citizen/resident spouse may allow eligibility for "
                "Lifetime Learning Credit via a IRC 6013(g)/(h) election to "
                "be treated as a resident for the full year. This is a "
                "significant, largely irreversible election a tax "
                "professional should be consulted before proceeding, not "
                "decided automatically here."
            ),
            estimated_amount=None,
        ),
        CreditEvaluationResult(
            source_type="NJ_DEDUCTION",
            rule_code="NJ_TUITION_DEDUCTION",
            status="ELIGIBLE",
            reason="Eligible for NJ College Tuition Deduction (up to $10,000 "
                   "for full-time enrollment at a New Jersey institution).",
            estimated_amount=8000.0,
        ),
        CreditEvaluationResult(
            source_type="TREATY_BENEFIT",
            rule_code="US_IND_ART21_2",
            status="INELIGIBLE",
            reason="Article 21(2) standard deduction benefit is exclusively "
                   "restricted to citizens/nationals of India.",
            estimated_amount=0.0,
        ),
    ]

    return residency, credit_evaluations


def verify_report(report, original_credit_evaluations):
    """Checks the STRUCTURAL guardrails, the things that must be true
    regardless of how the LLM's happens to read this time."""
    errors = []

    if report.disclaimer != MANDATORY_DISCLAIMER:
        errors.append("Disclaimer does not exactly match MANDATORY_DISCLAIMER.")

    real_status_by_code = {r.rule_code: r.status for r in original_credit_evaluations}
    for item in report.credit_breakdown:
        if item["rule_code"] not in real_status_by_code:
            errors.append(f"Report references unknown rule_code: {item['rule_code']}")
            continue
        if item["status"] != real_status_by_code[item["rule_code"]]:
            errors.append(
                f"Status mismatch for {item['rule_code']}: "
                f"report says {item['status']}, engine says "
                f"{real_status_by_code[item['rule_code']]}"
            )

    reported_codes = {item["rule_code"] for item in report.credit_breakdown}
    for r in original_credit_evaluations:
        if r.rule_code not in reported_codes:
            errors.append(f"Engine result for {r.rule_code} missing from report entirely.")

    warnings = []
    for item in report.credit_breakdown:
        if (
            real_status_by_code.get(item["rule_code"]) == "NEEDS_DOCUMENTATION"
            and "you are eligible" in item["explanation"].lower()
        ):
            warnings.append(
                f"WARNING: {item['rule_code']} explanation contains an "
                "unqualified eligibility claim despite NEEDS_DOCUMENTATION "
                "status — review this manually."
            )
    return errors, warnings


if __name__ == "__main__":
    residency, credit_evaluations = build_scenario()
    print("Calling Claude for explanation synthesis...\n")
    report = generate_explanation_report(residency, credit_evaluations)

    print("=" * 70)
    print("EXECUTIVE SUMMARY")
    print("=" * 70)
    print(report.executive_summary)

    print("\n" + "=" * 70)
    print("RESIDENCY BREAKDOWN")
    print("=" * 70)
    print(report.residency_breakdown)

    print("\n" + "=" * 70)
    print("CREDIT BREAKDOWN")
    print("=" * 70)
    for item in report.credit_breakdown:
        print(f"\n[{item['rule_code']}] status={item['status']}")
        print(item["explanation"])

    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    for step in report.next_steps:
        print(f"- {step}")

    print("\n" + "=" * 70)
    print("DISCLAIMER")
    print("=" * 70)
    print(report.disclaimer)

    print("\n" + "=" * 70)
    print("GUARDRAIL VERIFICATION")
    print("=" * 70)
    errors, warnings = verify_report(report, credit_evaluations)

    if errors:
        print("FAILED, structural guardrail violations found:")
        for e in errors:
            print(f"  x {e}")
    else:
        print("PASSED, all structural guardrails held.")

    if warnings:
        print("\nWarnings (manual review suggested):")
        for w in warnings:
            print(f"  ! {w}")