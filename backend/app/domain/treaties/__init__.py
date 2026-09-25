"""Per-country tax treaty plugins. Each module exposes one handler with the
signature (ResidencyDetermination, QuestionnaireInput) -> CreditEvaluationResult
and is registered in app.domain.treaty_engine.TREATY_HANDLERS."""
