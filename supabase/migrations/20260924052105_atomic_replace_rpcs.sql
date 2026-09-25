create or replace function public.replace_credit_evaluations(
  p_user_id  uuid,
  p_tax_year integer,
  p_rows     jsonb
)
returns integer
language plpgsql
security invoker
set search_path = ''
as $$
declare
  inserted integer;
begin
  if p_user_id is null or p_tax_year is null then
    raise exception 'p_user_id and p_tax_year are required';
  end if;
  if p_rows is null or jsonb_typeof(p_rows) <> 'array' then
    raise exception 'p_rows must be a JSON array';
  end if;

  perform pg_advisory_xact_lock(hashtextextended(p_user_id::text || ':' || p_tax_year::text, 0));

  delete from public.credit_evaluations
   where user_id = p_user_id
     and tax_year = p_tax_year;

  insert into public.credit_evaluations (
    user_id, tax_year, source_type, federal_credit_code, nj_rule_code,
    treaty_country_code, status, reason, estimated_amount,
    based_on_residency_determination_id
  )
  select
    p_user_id, p_tax_year, r.source_type, r.federal_credit_code, r.nj_rule_code,
    r.treaty_country_code, r.status, r.reason, r.estimated_amount,
    r.based_on_residency_determination_id
  from jsonb_populate_recordset(null::public.credit_evaluations, p_rows) as r;

  get diagnostics inserted = row_count;
  return inserted;
end;
$$;

revoke all on function public.replace_credit_evaluations(uuid, integer, jsonb)
  from public, anon, authenticated;
grant execute on function public.replace_credit_evaluations(uuid, integer, jsonb)
  to service_role;

create or replace function public.replace_visa_status_periods(p_periods jsonb)
returns integer
language plpgsql
security invoker           
set search_path = ''
as $$
declare
  uid uuid := auth.uid();
  inserted integer;
begin
  if uid is null then
    raise exception 'not authenticated' using errcode = '42501';
  end if;
  if p_periods is null or jsonb_typeof(p_periods) <> 'array' then
    raise exception 'p_periods must be a JSON array';
  end if;
  if jsonb_array_length(p_periods) > 20 then
    raise exception 'too many visa periods';
  end if;

  perform pg_advisory_xact_lock(hashtextextended(uid::text || ':visa', 0));

  delete from public.visa_status_periods where user_id = uid;

  insert into public.visa_status_periods
    (user_id, visa_type, start_date, end_date, is_exempt_status)
  select uid, r.visa_type, r.start_date, r.end_date, r.is_exempt_status
  from jsonb_populate_recordset(null::public.visa_status_periods, p_periods) as r;

  get diagnostics inserted = row_count;
  return inserted;
end;
$$;

revoke all on function public.replace_visa_status_periods(jsonb) from public, anon;
grant execute on function public.replace_visa_status_periods(jsonb) to authenticated;
