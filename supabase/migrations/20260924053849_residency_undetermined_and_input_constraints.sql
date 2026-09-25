-- =============================================================================
-- Task 6: UNDETERMINED residency status
-- Task 7: employment_type / filing_status constrained to the same values as
--         the Pydantic enums (backend/app/domain/schemas.py) and the Zod enums
--         (ai-audit-agent/lib/utils/validation/questionnaire.ts).
-- =============================================================================

-- ALTER TYPE ... ADD VALUE is idempotent with IF NOT EXISTS and cannot be
-- used by later statements in the same transaction — nothing below uses it.
alter type public.tax_residency_enum add value if not exists 'UNDETERMINED';

-- NOT VALID: enforced for every new/updated row immediately, without failing
-- on legacy rows. After cleaning any legacy values, run:
--   alter table public.questionnaire_responses
--     validate constraint questionnaire_responses_employment_type_check;
--   alter table public.questionnaire_responses
--     validate constraint questionnaire_responses_filing_status_check;
alter table public.questionnaire_responses
  drop constraint if exists questionnaire_responses_employment_type_check;
alter table public.questionnaire_responses
  add constraint questionnaire_responses_employment_type_check
  check (employment_type in ('W2','CONTRACTOR_1099','UNEMPLOYED','STUDENT_WORKER'))
  not valid;

alter table public.questionnaire_responses
  drop constraint if exists questionnaire_responses_filing_status_check;
alter table public.questionnaire_responses
  add constraint questionnaire_responses_filing_status_check
  check (filing_status in (
    'SINGLE','MARRIED_FILING_JOINTLY','MARRIED_FILING_SEPARATELY',
    'HEAD_OF_HOUSEHOLD','QUALIFYING_SURVIVING_SPOUSE'))
  not valid;

-- Credit/deduction status values produced by the engines.
alter table public.credit_evaluations
  drop constraint if exists credit_evaluations_status_check;
alter table public.credit_evaluations
  add constraint credit_evaluations_status_check
  check (status in ('ELIGIBLE','NEEDS_DOCUMENTATION','INELIGIBLE','NOT_APPLICABLE'))
  not valid;
