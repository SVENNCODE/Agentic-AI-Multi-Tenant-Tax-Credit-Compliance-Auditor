"""
Treaty engine dispatcher.
Maps a taxpayer's citizenship country (ISO-3166 alpha-3) to the plugin that
evaluates that country's US income tax treaty.
"""

from typing import Callable, Dict

from app.domain.schemas import (
    CreditEvaluationResult,
    QuestionnaireInput,
    ResidencyDetermination,
)
from app.domain.treaties.india import evaluate_india_treaty_benefit

TreatyHandler = Callable[[ResidencyDetermination, QuestionnaireInput], CreditEvaluationResult]

# Active, verified plugins only.
TREATY_HANDLERS: Dict[str, TreatyHandler] = {
    "IND": evaluate_india_treaty_benefit,
}

UNSUPPORTED_RULE_CODE = "TREATY_NOT_EVALUATED"


def supported_countries() -> list[str]:
    return sorted(TREATY_HANDLERS)


def get_treaty_handler(country_code: str) -> TreatyHandler:
    code = (country_code or "").strip().upper()
    try:
        return TREATY_HANDLERS[code]
    except KeyError:
        raise NotImplementedError(
            f"No verified treaty plugin is registered for country '{code}'."
        ) from None


def evaluate_treaty_benefit(
    residency: ResidencyDetermination,
    questionnaire: QuestionnaireInput,
) -> CreditEvaluationResult:
    code = (questionnaire.citizenship_country or "").strip().upper()
    try:
        handler = get_treaty_handler(code)
    except NotImplementedError:
        return CreditEvaluationResult(
            source_type="TREATY_BENEFIT",
            rule_code=UNSUPPORTED_RULE_CODE,
            status="NOT_APPLICABLE",
            reason=(
                f"Tax treaty benefits for citizens of {code or 'this country'} "
                "are not evaluated by this tool yet. A tax professional can "
                "confirm whether a treaty benefit applies to you."
            ),
            estimated_amount=None,
            country_code=code or None,
        )
    return handler(residency, questionnaire)
