-- Role 4 persistence for the hosted Supabase project.
-- Does not drop or replace public.patients or public.history_notes.
-- Apply in the SQL Editor: https://supabase.com/dashboard/project/pjrhqtehfofgrhcdjtsh/sql/new
--
-- Access model: Role 3/4 Python is the intended client. Until a secret key
-- is available, demo policies allow the publishable key (anon) to use these
-- tables. Revoke anon grants and drop the *_demo policies when the backend
-- has SUPABASE_SECRET_KEY.

create table if not exists public.schema_migrations (
  version bigint primary key,
  name text not null,
  applied_at timestamptz not null default now()
);

create table if not exists public.cases (
  id bigint generated always as identity primary key,
  public_id text unique not null,
  patient_id bigint not null references public.patients(id) on delete restrict,
  status text not null default 'open'
    check (status in ('open','approved','rejected','resolved','purged')),
  case_version integer not null default 0,
  urgency_score double precision default 0.0,
  summary_enc text,
  idempotency_key text unique,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.case_keys (
  id bigint generated always as identity primary key,
  case_id bigint unique not null references public.cases(id) on delete restrict,
  case_key_enc text not null,
  idempotency_key text unique,
  created_at timestamptz not null default now()
);

create table if not exists public.sessions (
  id bigint generated always as identity primary key,
  public_id text unique not null,
  case_id bigint not null references public.cases(id) on delete restrict,
  transcript_ref text,
  sentiment text default 'okay' check (sentiment in ('calm','distressed','okay')),
  wpm double precision default 120.0,
  disfluency_count integer default 0,
  idempotency_key text unique,
  created_at timestamptz not null default now()
);

create table if not exists public.reviews (
  id bigint generated always as identity primary key,
  public_id text unique not null,
  case_id bigint not null references public.cases(id) on delete restrict,
  reviewer_id text not null,
  reviewer_role text not null,
  decision text not null check (decision in ('approved','rejected')),
  base_case_version integer,
  idempotency_key text unique not null,
  created_at timestamptz not null default now()
);

create table if not exists public.review_payloads (
  id bigint generated always as identity primary key,
  review_id bigint unique not null references public.reviews(id) on delete restrict,
  notes_enc text,
  edits_json_enc text,
  idempotency_key text unique not null,
  created_at timestamptz not null default now()
);

create table if not exists public.approved_records (
  id bigint generated always as identity primary key,
  public_id text unique not null,
  case_id bigint unique not null references public.cases(id) on delete restrict,
  patient_id bigint not null references public.patients(id) on delete restrict,
  review_id bigint not null references public.reviews(id) on delete restrict,
  case_version integer not null,
  esi_level integer check (esi_level is null or (esi_level between 1 and 5)),
  final_triage_code text not null,
  final_triage_label text not null,
  attending_clinician text not null,
  digital_signature text not null,
  idempotency_key text unique not null,
  approved_at timestamptz not null default now()
);

create table if not exists public.approved_record_payloads (
  id bigint generated always as identity primary key,
  approved_record_id bigint unique not null references public.approved_records(id) on delete restrict,
  chief_complaint_enc text not null,
  sbar_situation_enc text not null,
  sbar_background_enc text not null,
  sbar_assessment_enc text not null,
  sbar_recommendation_enc text not null,
  triage_rationale_enc text,
  idempotency_key text unique not null,
  created_at timestamptz not null default now()
);

create table if not exists public.audit_log (
  id bigint generated always as identity primary key,
  entity_type text not null,
  action text not null,
  actor_id text not null,
  actor_role text not null,
  entity_id bigint not null,
  details_sanitized text,
  prev_entry_hmac text not null,
  entry_hmac text not null,
  idempotency_key text unique not null,
  created_at timestamptz not null default now()
);

create index if not exists cases_patient_id_idx on public.cases (patient_id);
create index if not exists cases_public_id_idx on public.cases (public_id);
create index if not exists sessions_case_id_idx on public.sessions (case_id);
create index if not exists reviews_case_id_idx on public.reviews (case_id);
create index if not exists approved_records_case_id_idx on public.approved_records (case_id);
create index if not exists approved_records_patient_id_idx on public.approved_records (patient_id);
create index if not exists history_notes_patient_id_idx on public.history_notes (patient_id);
create index if not exists patients_phone_number_idx on public.patients (phone_number);
create index if not exists audit_log_entity_idx on public.audit_log (entity_type, entity_id);

create or replace function public.aria_reject_mutation()
returns trigger
language plpgsql
as $$
begin
  raise exception '% is immutable', tg_table_name;
end;
$$;

drop trigger if exists trg_rev_upd on public.reviews;
drop trigger if exists trg_rev_del on public.reviews;
create trigger trg_rev_upd before update on public.reviews
  for each row execute procedure public.aria_reject_mutation();
create trigger trg_rev_del before delete on public.reviews
  for each row execute procedure public.aria_reject_mutation();

drop trigger if exists trg_rpl_upd on public.review_payloads;
drop trigger if exists trg_rpl_del on public.review_payloads;
create trigger trg_rpl_upd before update on public.review_payloads
  for each row execute procedure public.aria_reject_mutation();
create trigger trg_rpl_del before delete on public.review_payloads
  for each row execute procedure public.aria_reject_mutation();

drop trigger if exists trg_app_upd on public.approved_records;
drop trigger if exists trg_app_del on public.approved_records;
create trigger trg_app_upd before update on public.approved_records
  for each row execute procedure public.aria_reject_mutation();
create trigger trg_app_del before delete on public.approved_records
  for each row execute procedure public.aria_reject_mutation();

drop trigger if exists trg_apl_upd on public.approved_record_payloads;
drop trigger if exists trg_apl_del on public.approved_record_payloads;
create trigger trg_apl_upd before update on public.approved_record_payloads
  for each row execute procedure public.aria_reject_mutation();
create trigger trg_apl_del before delete on public.approved_record_payloads
  for each row execute procedure public.aria_reject_mutation();

drop trigger if exists trg_aud_upd on public.audit_log;
drop trigger if exists trg_aud_del on public.audit_log;
create trigger trg_aud_upd before update on public.audit_log
  for each row execute procedure public.aria_reject_mutation();
create trigger trg_aud_del before delete on public.audit_log
  for each row execute procedure public.aria_reject_mutation();

alter table public.cases enable row level security;
alter table public.case_keys enable row level security;
alter table public.sessions enable row level security;
alter table public.reviews enable row level security;
alter table public.review_payloads enable row level security;
alter table public.approved_records enable row level security;
alter table public.approved_record_payloads enable row level security;
alter table public.audit_log enable row level security;
alter table public.schema_migrations enable row level security;
alter table public.patients enable row level security;
alter table public.history_notes enable row level security;

grant select, insert, update on table public.cases to anon, authenticated, service_role;
grant select, insert, update, delete on table public.case_keys to anon, authenticated, service_role;
grant select, insert on table public.sessions to anon, authenticated, service_role;
grant select, insert on table public.reviews to anon, authenticated, service_role;
grant select, insert on table public.review_payloads to anon, authenticated, service_role;
grant select, insert on table public.approved_records to anon, authenticated, service_role;
grant select, insert on table public.approved_record_payloads to anon, authenticated, service_role;
grant select, insert on table public.audit_log to anon, authenticated, service_role;
grant select, insert on table public.schema_migrations to anon, authenticated, service_role;
grant select, insert, update on table public.patients to anon, authenticated, service_role;
grant select, insert, update on table public.history_notes to anon, authenticated, service_role;
grant usage, select on all sequences in schema public to anon, authenticated, service_role;

drop policy if exists cases_select_demo on public.cases;
drop policy if exists cases_insert_demo on public.cases;
drop policy if exists cases_update_demo on public.cases;
create policy cases_select_demo on public.cases for select to anon, authenticated using (true);
create policy cases_insert_demo on public.cases for insert to anon, authenticated with check (true);
create policy cases_update_demo on public.cases for update to anon, authenticated using (true) with check (true);

drop policy if exists case_keys_select_demo on public.case_keys;
drop policy if exists case_keys_insert_demo on public.case_keys;
drop policy if exists case_keys_update_demo on public.case_keys;
drop policy if exists case_keys_delete_demo on public.case_keys;
create policy case_keys_select_demo on public.case_keys for select to anon, authenticated using (true);
create policy case_keys_insert_demo on public.case_keys for insert to anon, authenticated with check (true);
create policy case_keys_update_demo on public.case_keys for update to anon, authenticated using (true) with check (true);
create policy case_keys_delete_demo on public.case_keys for delete to anon, authenticated using (true);

drop policy if exists sessions_select_demo on public.sessions;
drop policy if exists sessions_insert_demo on public.sessions;
create policy sessions_select_demo on public.sessions for select to anon, authenticated using (true);
create policy sessions_insert_demo on public.sessions for insert to anon, authenticated with check (true);

drop policy if exists reviews_select_demo on public.reviews;
drop policy if exists reviews_insert_demo on public.reviews;
create policy reviews_select_demo on public.reviews for select to anon, authenticated using (true);
create policy reviews_insert_demo on public.reviews for insert to anon, authenticated with check (true);

drop policy if exists review_payloads_select_demo on public.review_payloads;
drop policy if exists review_payloads_insert_demo on public.review_payloads;
create policy review_payloads_select_demo on public.review_payloads for select to anon, authenticated using (true);
create policy review_payloads_insert_demo on public.review_payloads for insert to anon, authenticated with check (true);

drop policy if exists approved_records_select_demo on public.approved_records;
drop policy if exists approved_records_insert_demo on public.approved_records;
create policy approved_records_select_demo on public.approved_records for select to anon, authenticated using (true);
create policy approved_records_insert_demo on public.approved_records for insert to anon, authenticated with check (true);

drop policy if exists approved_record_payloads_select_demo on public.approved_record_payloads;
drop policy if exists approved_record_payloads_insert_demo on public.approved_record_payloads;
create policy approved_record_payloads_select_demo on public.approved_record_payloads for select to anon, authenticated using (true);
create policy approved_record_payloads_insert_demo on public.approved_record_payloads for insert to anon, authenticated with check (true);

drop policy if exists audit_log_select_demo on public.audit_log;
drop policy if exists audit_log_insert_demo on public.audit_log;
create policy audit_log_select_demo on public.audit_log for select to anon, authenticated using (true);
create policy audit_log_insert_demo on public.audit_log for insert to anon, authenticated with check (true);

drop policy if exists schema_migrations_select_demo on public.schema_migrations;
drop policy if exists schema_migrations_insert_demo on public.schema_migrations;
create policy schema_migrations_select_demo on public.schema_migrations for select to anon, authenticated using (true);
create policy schema_migrations_insert_demo on public.schema_migrations for insert to anon, authenticated with check (true);

drop policy if exists patients_select_demo on public.patients;
drop policy if exists patients_insert_demo on public.patients;
drop policy if exists patients_update_demo on public.patients;
create policy patients_select_demo on public.patients for select to anon, authenticated using (true);
create policy patients_insert_demo on public.patients for insert to anon, authenticated with check (true);
create policy patients_update_demo on public.patients for update to anon, authenticated using (true) with check (true);

drop policy if exists history_notes_select_demo on public.history_notes;
drop policy if exists history_notes_insert_demo on public.history_notes;
drop policy if exists history_notes_update_demo on public.history_notes;
create policy history_notes_select_demo on public.history_notes for select to anon, authenticated using (true);
create policy history_notes_insert_demo on public.history_notes for insert to anon, authenticated with check (true);
create policy history_notes_update_demo on public.history_notes for update to anon, authenticated using (true) with check (true);

insert into public.schema_migrations (version, name)
values (1, '001_role4_persistence')
on conflict (version) do nothing;

revoke execute on function public.aria_reject_mutation() from public, anon, authenticated;

notify pgrst, 'reload schema';
