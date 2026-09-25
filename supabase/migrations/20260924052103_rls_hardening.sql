-- =============================================================================
-- RLS HARDENING — makes row-level security the enforced source of truth.
-- Audit finding D1: every browser/API path that uses the anon/publishable key
-- relies on these policies. This migration:
--   1. enables (and forces) RLS on every application table,
--   2. DROPS every existing policy on those tables (permissive policies are
--      OR'ed together, so one stale "allow all" policy would defeat the rest),
--   3. recreates the minimum set of policies the application needs,
--   4. revokes table privileges that end users must never have.
-- Review the DROP step before pushing if you have hand-written policies you
-- want to keep — re-add them below instead.
-- =============================================================================

do $$
declare
  t text;
  p record;
begin
  foreach t in array array[
    'profiles','questionnaire_responses','visa_status_periods',
    'residency_determinations','credit_evaluations',
    'spt_rules','federal_credit_rules'
  ] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('alter table public.%I force row level security', t);
    for p in
      select policyname from pg_policies
      where schemaname = 'public' and tablename = t
    loop
      execute format('drop policy %I on public.%I', p.policyname, t);
    end loop;
  end loop;
end $$;

-- ---- Table privileges ------------------------------------------------------
-- The anonymous role never touches application data.
revoke all on public.profiles, public.questionnaire_responses,
              public.visa_status_periods, public.residency_determinations,
              public.credit_evaluations, public.spt_rules,
              public.federal_credit_rules
  from anon;

-- Results and rule tables are READ-ONLY for signed-in users. Only the
-- backend's service role (which bypasses RLS) may write them.
revoke insert, update, delete, truncate on
  public.residency_determinations, public.credit_evaluations,
  public.spt_rules, public.federal_credit_rules
  from authenticated;
grant select on
  public.residency_determinations, public.credit_evaluations,
  public.spt_rules, public.federal_credit_rules
  to authenticated;

grant select, insert, update, delete on
  public.profiles, public.questionnaire_responses, public.visa_status_periods
  to authenticated;
revoke truncate on
  public.profiles, public.questionnaire_responses, public.visa_status_periods
  from authenticated;

-- ---- Policies: user-owned input tables --------------------------------------
-- (select auth.uid()) is evaluated once per statement (Supabase perf guidance).

create policy profiles_select_own on public.profiles
  for select to authenticated using (user_id = (select auth.uid()));
create policy profiles_insert_own on public.profiles
  for insert to authenticated with check (user_id = (select auth.uid()));
create policy profiles_update_own on public.profiles
  for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

create policy questionnaire_select_own on public.questionnaire_responses
  for select to authenticated using (user_id = (select auth.uid()));
create policy questionnaire_insert_own on public.questionnaire_responses
  for insert to authenticated with check (user_id = (select auth.uid()));
create policy questionnaire_update_own on public.questionnaire_responses
  for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));
create policy questionnaire_delete_own on public.questionnaire_responses
  for delete to authenticated using (user_id = (select auth.uid()));

create policy visa_periods_select_own on public.visa_status_periods
  for select to authenticated using (user_id = (select auth.uid()));
create policy visa_periods_insert_own on public.visa_status_periods
  for insert to authenticated with check (user_id = (select auth.uid()));
create policy visa_periods_update_own on public.visa_status_periods
  for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));
create policy visa_periods_delete_own on public.visa_status_periods
  for delete to authenticated using (user_id = (select auth.uid()));

-- ---- Policies: backend-authored results (read own only) ----------------------
create policy residency_select_own on public.residency_determinations
  for select to authenticated using (user_id = (select auth.uid()));
create policy credit_evals_select_own on public.credit_evaluations
  for select to authenticated using (user_id = (select auth.uid()));

-- ---- Policies: reference data (readable by any signed-in user) ---------------
create policy spt_rules_read on public.spt_rules
  for select to authenticated using (true);
create policy federal_credit_rules_read on public.federal_credit_rules
  for select to authenticated using (true);
