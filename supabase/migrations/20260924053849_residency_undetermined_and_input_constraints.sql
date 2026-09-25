alter type public.tax_residency_enum add value if not exists 'UNDETERMINED';

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

alter table public.credit_evaluations
  drop constraint if exists credit_evaluations_status_check;
alter table public.credit_evaluations
  add constraint credit_evaluations_status_check
  check (status in ('ELIGIBLE','NEEDS_DOCUMENTATION','INELIGIBLE','NOT_APPLICABLE'))
  not valid;
