"""
AuditGraphState — the state object that flows through every node in the
Orchestrator graph. This mirrors, stage by stage, what
questionnaire_route.py currently does imperatively (write questionnaire ->
determine residency -> write -> evaluate credits -> write -> synthesize
explanation) — the graph is meant to REPLACE that linear try/except
sequence with explicit nodes and edges, not duplicate it alongside it.
"""

import operator
from enum import Enum
from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.domain.schemas import (
    QuestionnaireInput,
    ResidencyDetermination,
    CreditEvaluationResult,
)
from app.agents.explanation_engine import ExplanationReport


class StepStatus(str, Enum):
    """Per-stage status, so the graph (and anything inspecting state
    mid-run, like a future Dashboard) can tell exactly where a given
    audit run is, or where it failed."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class AuditGraphState(BaseModel):
    # ---- Identity / entry context — set once, before the graph starts ----
    user_id: str
    tax_year: int
    questionnaire: QuestionnaireInput

    # ---- Stage 1: Residency determination ----
    residency_determination: Optional[ResidencyDetermination] = None
    # Set only after the DB write succeeds — used later to link
    # credit_evaluations rows via based_on_residency_determination_id,
    # same field your route already writes today.
    residency_determination_id: Optional[str] = None
    residency_step_status: StepStatus = StepStatus.PENDING

    # ---- Stage 2: Credit / deduction / treaty evaluations ----
    # A single flat list across all three source_types (FEDERAL_CREDIT,
    # NJ_DEDUCTION, TREATY_BENEFIT) — matches how credit_evaluations rows
    # are already structured, rather than three separate lists that would
    # need re-merging later.
    credit_evaluations: List[CreditEvaluationResult] = Field(default_factory=list)
    credit_evaluation_step_status: StepStatus = StepStatus.PENDING

    # ---- Stage 3: Explanation synthesis (the only LLM-touched stage) ----
    explanation_report: Optional[ExplanationReport] = None
    explanation_step_status: StepStatus = StepStatus.PENDING

    # ---- Stage 4: Persistence confirmation ----
    # Tracks whether everything computed above actually made it to the DB
    # — a run can compute a correct result but still fail here (a Supabase
    # write error), which is a meaningfully different failure than a bad
    # determination.
    persisted: bool = False
    persistence_step_status: StepStatus = StepStatus.PENDING

    # ---- Error tracking ----
    # Annotated with operator.add: every node that hits a problem APPENDS
    # to this list rather than overwriting whatever a previous node
    # already recorded. Without this annotation, only the LAST node's
    # error would survive — a real bug this specific field is designed to
    # prevent, given LangGraph's default last-write-wins per-key merge.
    errors: Annotated[List[str], operator.add] = Field(default_factory=list)

    # ---- Observability / auditability ----
    # Not annotated with a reducer: nodes read-copy-update-return the full
    # dict manually (see run_residency example), which is correct as long
    # as the graph stays sequential. If parallel node execution is ever
    # added, this needs a proper dict-merge reducer — see the note in the
    # accompanying design discussion.
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # ---- Overall run status ----
    is_complete: bool = False