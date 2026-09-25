// Migration test harness: applies supabase/migrations/*.sql to an in-process
// Postgres (PGlite) with minimal Supabase stubs and checks RLS + RPC behaviour.
// Run:  cd supabase/tests && npm i --no-save @electric-sql/pglite && node db.test.mjs ../migrations
import { PGlite } from "@electric-sql/pglite";
import fs from "node:fs";
import assert from "node:assert/strict";

const MIG = process.argv[2];
const db = new PGlite();
const A = "11111111-1111-1111-1111-111111111111";
const B = "22222222-2222-2222-2222-222222222222";

// ---- Minimal Supabase platform stubs (roles, auth schema, auth.uid()) ----
await db.exec(`
  create role anon nologin; create role authenticated nologin; create role service_role nologin bypassrls;
  create schema auth;
  create table auth.users (id uuid primary key);
  create function auth.uid() returns uuid language sql stable as
    $$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
  grant usage on schema auth to anon, authenticated, service_role;
  grant execute on function auth.uid() to anon, authenticated, service_role;
  grant usage on schema public to anon, authenticated, service_role;
  alter default privileges in schema public grant all on tables to anon, authenticated, service_role;
  alter default privileges in schema public grant all on functions to anon, authenticated, service_role;
  insert into auth.users values ('${A}'), ('${B}');
`);

for (const f of fs.readdirSync(MIG).filter((f) => f.endsWith(".sql")).sort()) {
  await db.exec(fs.readFileSync(`${MIG}/${f}`, "utf8"));
  console.log("applied", f);
}
await db.exec(`grant all on all tables in schema public to service_role;`);

async function as(role, sub, fn) {
  await db.exec(`reset role; select set_config('request.jwt.claim.sub', '${sub ?? ""}', false); set role ${role};`);
  try { return await fn(); } finally { await db.exec("reset role;"); }
}
const rows = (n, status = "ELIGIBLE") => JSON.stringify(Array.from({ length: n }, (_, i) => ({
  source_type: "FEDERAL_CREDIT", federal_credit_code: `C${i}`, status, reason: "r", estimated_amount: 1,
  user_id: B, tax_year: 1999, // must be IGNORED by the RPC
})));
const count = async (sub) => (await db.query(`select count(*)::int c from public.credit_evaluations where user_id = $1 and tax_year = 2025`, [sub])).rows[0].c;

// 1. service_role replaces atomically
await as("service_role", null, () => db.query(`select public.replace_credit_evaluations($1, 2025, $2::jsonb)`, [A, rows(3)]));
assert.equal(await count(A), 3); assert.equal(await count(B), 0);
await as("service_role", null, () => db.query(`select public.replace_credit_evaluations($1, 2025, $2::jsonb)`, [A, rows(2)]));
assert.equal(await count(A), 2, "replace, not append");
console.log("PASS replace_credit_evaluations replaces rows and ignores payload user_id/tax_year");

// 2. a failing insert rolls back the delete (atomicity)
const bad = JSON.stringify([{ source_type: "FEDERAL_CREDIT", status: "ELIGIBLE" }, { source_type: "X", status: "BOGUS" }]);
await assert.rejects(as("service_role", null, () => db.query(`select public.replace_credit_evaluations($1, 2025, $2::jsonb)`, [A, bad])));
assert.equal(await count(A), 2, "previous rows must survive a failed replace");
console.log("PASS failed replace rolls back — no data loss");

// 3. authenticated users cannot call the service RPC or write results/rules
await assert.rejects(as("authenticated", A, () => db.query(`select public.replace_credit_evaluations($1, 2025, '[]'::jsonb)`, [A])));
await assert.rejects(as("authenticated", A, () => db.query(`insert into public.credit_evaluations (user_id,tax_year,source_type,status) values ($1,2025,'X','ELIGIBLE')`, [A])));
await assert.rejects(as("authenticated", A, () => db.query(`insert into public.spt_rules values (2025,31,183,0.33,0.16)`)));
console.log("PASS users cannot write credit_evaluations / rule tables or call the service RPC");

// 4. tenant isolation on reads
await as("service_role", null, () => db.query(`select public.replace_credit_evaluations($1, 2025, $2::jsonb)`, [B, rows(1)]));
const seenByA = await as("authenticated", A, () => db.query(`select user_id from public.credit_evaluations`));
assert.ok(seenByA.rows.length === 2 && seenByA.rows.every((r) => r.user_id === A));
console.log("PASS user A sees only own credit_evaluations");

// 5. visa RPC runs as caller and forces user_id = auth.uid()
const periods = JSON.stringify([{ user_id: B, visa_type: "F1", start_date: "2022-08-15", is_exempt_status: true }]);
await as("authenticated", A, () => db.query(`select public.replace_visa_status_periods($1::jsonb)`, [periods]));
await as("authenticated", A, () => db.query(`select public.replace_visa_status_periods($1::jsonb)`, [periods]));
const v = (await db.query(`select user_id from public.visa_status_periods`)).rows;
assert.equal(v.length, 1); assert.equal(v[0].user_id, A);
await assert.rejects(as("anon", null, () => db.query(`select public.replace_visa_status_periods('[]'::jsonb)`)));
console.log("PASS replace_visa_status_periods is atomic, owner-forced, anon-denied");

// 6. anon has no access; users cannot update another user's profile
await assert.rejects(as("anon", null, () => db.query(`select * from public.profiles`)));
await as("service_role", null, () => db.query(`insert into public.profiles (user_id) values ($1), ($2)`, [A, B]));
const upd = await as("authenticated", A, () => db.query(`update public.profiles set citizenship_country='XXX' where user_id = $1`, [B]));
assert.equal(upd.affectedRows, 0);
await assert.rejects(as("authenticated", A, () => db.query(`update public.profiles set user_id = $1 where user_id = $2`, [B, A])));
console.log("PASS anon denied; cross-user profile update/ownership change blocked");

// 7. enum + constraints
await as("service_role", null, () => db.query(`insert into public.residency_determinations (user_id,tax_year,determined_residency) values ($1,2025,'UNDETERMINED')`, [A]));
await assert.rejects(as("authenticated", A, () => db.query(`insert into public.questionnaire_responses (user_id,tax_year,employment_type) values ($1,2025,'ASTRONAUT')`, [A])));
await as("authenticated", A, () => db.query(`insert into public.questionnaire_responses (user_id,tax_year,employment_type,filing_status) values ($1,2025,'W2','SINGLE')`, [A]));
await assert.rejects(as("authenticated", A, () => db.query(`insert into public.questionnaire_responses (user_id,tax_year) values ($1,2024)`, [B])));
console.log("PASS UNDETERMINED accepted; employment_type constraint enforced; RLS WITH CHECK blocks spoofed user_id");
console.log("ALL DB TESTS PASSED");
