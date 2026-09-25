import pytest

from app.domain import treaty_engine
from app.domain.schemas import ResidencyStatus
from app.domain.treaties.india import evaluate_india_treaty_benefit
from tests.test_treaty_india_engine import make_questionnaire, make_residency


def test_india_is_registered_plugin():
    assert treaty_engine.supported_countries() == ["IND"]
    assert treaty_engine.get_treaty_handler("ind") is evaluate_india_treaty_benefit


def test_strict_lookup_raises_for_unverified_country():
    with pytest.raises(NotImplementedError):
        treaty_engine.get_treaty_handler("CHN")


def test_dispatch_routes_india_to_plugin():
    result = treaty_engine.evaluate_treaty_benefit(
        make_residency(ResidencyStatus.NONRESIDENT_ALIEN), make_questionnaire()
    )
    assert result.rule_code == "US_IND_ART21_2"
    assert result.status == "ELIGIBLE"
    assert result.country_code == "IND"


def test_dispatch_is_graceful_for_unsupported_country():
    result = treaty_engine.evaluate_treaty_benefit(
        make_residency(ResidencyStatus.NONRESIDENT_ALIEN),
        make_questionnaire(citizenship_country="CHN"),
    )
    assert result.source_type == "TREATY_BENEFIT"
    assert result.rule_code == treaty_engine.UNSUPPORTED_RULE_CODE
    assert result.status == "NOT_APPLICABLE"
    assert result.country_code == "CHN"
    assert result.estimated_amount is None


def test_undetermined_residency_needs_documentation():
    result = treaty_engine.evaluate_treaty_benefit(
        make_residency(ResidencyStatus.UNDETERMINED), make_questionnaire()
    )
    assert result.status == "NEEDS_DOCUMENTATION"


def test_legacy_import_path_still_works():
    from app.domain.treaty_india_engine import evaluate_india_treaty_benefit as legacy
    assert legacy is evaluate_india_treaty_benefit
