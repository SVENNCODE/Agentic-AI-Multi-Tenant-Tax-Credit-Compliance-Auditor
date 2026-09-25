-- =============================================================================
-- BASELINE SCHEMA (reconstructed from application code on 2026-09-24)
-- =============================================================================
-- IMPORTANT — READ BEFORE PUSHING:
--   This file was reconstructed from the column names the backend reads and
--   writes, because the audit environment could not reach the live database.
--   It is written to be IDEMPOTENT (IF NOT EXISTS everywhere) so it is safe on
--   a fresh local database, but the LIVE schema is the real source of truth.
--
--   Recommended workflow against the existing hosted project:
--     supabase link --project-ref <ref>
--     supabase db pull                   # writes the exact live schema as a new migration
--       -> replace the body of THIS file with that output, delete the pulled copy
--     supabase migration repair --status applied 20260924052100
--                                        # mark baseline as already applied remotely
--     supabase db push                   # applies only the migrations after it
-- =============================================================================

-- ---- Enums -----------------------------------------------------------------
do $$ begin
  create type public.visa_type_enum as enum
    ('F1','J1','M1','Q1','H1B','OPT','OTHER','NONE');
exception when duplicate_object then null; end $$;

do $$ begin
  create type public.tax_residency_enum as enum
    ('NONRESIDENT_ALIEN','RESIDENT_ALIEN','DUAL_STATUS');
exception when duplicate_object then null; end $$;

-- ---- User-owned tables -----------------------------------------------------
create table if not exists public.profiles (
  user_id             uuid primary key references auth.users(id) on delete cascade,
  citizenship_country text,
  us_entry_date       date,
  current_visa_type   public.visa_type_enum,
  created_at          timestamptz not null default now()
);

create table if not exists public.questionnaire_responses (
  id                            uuid primary key default gen_random_uuid(),
  user_id                       uuid not null references auth.users(id) on delete cascade,
  tax_year                      integer not null,
  state_of_residence            text,
  filing_status                 text,
  employment_type               text,
  is_fulltime_student           boolean,
  annual_income                 numeric,
  number_of_employers           integer,
  scholarship_amount            numeric,
  tuition_paid                  numeric,
  has_education_expenses        boolean,
  has_childcare_expenses        boolean,
  has_medical_expenses          boolean,
  has_charitable_donations      boolean,
  has_retirement_contributions  boolean,
  days_present_current_year     integer,
  days_present_prior_year       integer,
  days_present_two_years_prior  integer,
  raw_responses                 jsonb,
  is_completed                  boolean not null default false,
  created_at                    timestamptz not null default now(),
  unique (user_id, tax_year)
);

create table if not exists public.visa_status_periods (
  id               uuid primary key default gen_random_uuid(),
  user_id          uuid not null references auth.users(id) on delete cascade,
  visa_type        public.visa_type_enum not null,
  start_date       date not null,
  end_date         date,
  is_exempt_status boolean,
  created_at       timestamptz not null default now()
);

-- ---- Backend-authored results (written only by the service role) ------------
create table if not exists public.residency_determinations (
  id                         uuid primary key default gen_random_uuid(),
  user_id                    uuid not null references auth.users(id) on delete cascade,
  tax_year                   integer not null,
  days_present_current_year  integer,
  days_present_prev_year1    integer,
  days_present_prev_year2    integer,
  spt_weighted_days          numeric,
  is_exempt_individual       boolean,
  exempt_years_used          integer,
  determined_residency       public.tax_residency_enum,
  target_form                text,
  applied_treaty_code        text,
  audit_trail                jsonb,
  explanation_report         jsonb,
  run_metadata               jsonb,
  determined_at              timestamptz,
  unique (user_id, tax_year)
);

create table if not exists public.credit_evaluations (
  id                                   uuid primary key default gen_random_uuid(),
  user_id                              uuid not null references auth.users(id) on delete cascade,
  tax_year                             integer not null,
  source_type                          text not null,
  federal_credit_code                  text,
  nj_rule_code                         text,
  treaty_country_code                  text,
  status                               text not null,
  reason                               text,
  estimated_amount                     numeric,
  based_on_residency_determination_id  uuid references public.residency_determinations(id) on delete set null,
  created_at                           timestamptz not null default now()
);
create index if not exists credit_evaluations_user_year_idx
  on public.credit_evaluations (user_id, tax_year);

-- ---- Reference / rule tables (read-only for end users) ---------------------
create table if not exists public.spt_rules (
  tax_year              integer primary key,
  min_current_year_days integer not null,
  spt_threshold_days    integer not null,
  prev_year1_weight     numeric not null,
  prev_year2_weight     numeric not null
);

create table if not exists public.federal_credit_rules (
  tax_year                   integer not null,
  credit_code                text not null,
  credit_name                text not null,
  max_credit_amount          numeric not null,
  refundable_percentage      numeric not null,
  max_refundable_amount      numeric not null,
  expense_cap                numeric not null,
  max_years_claimable        integer,
  requires_ssn               boolean not null,
  allows_nonresident_aliens  boolean not null,
  min_enrollment_status      text not null,
  magi_phaseout_single_start numeric not null,
  magi_phaseout_single_end   numeric not null,
  magi_phaseout_mfj_start    numeric not null,
  magi_phaseout_mfj_end      numeric not null,
  notes                      text,
  primary key (tax_year, credit_code)
);
