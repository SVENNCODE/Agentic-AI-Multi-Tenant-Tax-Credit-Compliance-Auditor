from dataclasses import dataclass

from tenacity import retry, stop_after_attempt, wait_exponential

from app.domain.credit_engine import FederalCreditRule


@dataclass
class SPTRuleSet:
    min_current_year_days: int
    spt_threshold_days: int
    prior_year_weight: float
    two_years_prior_weight: float


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def fetch_spt_rules(service_client, tax_year: int) -> SPTRuleSet:
    response = (
        service_client.table("spt_rules")
        .select("*")
        .eq("tax_year", tax_year)
        .single()
        .execute()
    )
    row = response.data

    if row is None:
        raise ValueError(f"No spt_rules row found for tax_year={tax_year}")
    return SPTRuleSet(
        min_current_year_days=row["min_current_year_days"],
        spt_threshold_days=row["spt_threshold_days"],
        prior_year_weight=row["prev_year1_weight"],
        two_years_prior_weight=row["prev_year2_weight"],
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def fetch_federal_credit_rules(service_client, tax_year: int) -> list[FederalCreditRule]:
    """
    Same query already used inline in questionnaire_route.py today — just
    moved here and wrapped with retry, not new logic.
    """
    response = (
        service_client.table("federal_credit_rules")
        .select("*")
        .eq("tax_year", tax_year)
        .execute()
    )
    return [FederalCreditRule(**row) for row in response.data]