-- Qyvox stores the verification result and an exact-proof replay fingerprint.
-- It never stores date of birth, birth year, age, document imagery, or circuit
-- witness material.
create table if not exists public.verified_users (
  user_id uuid primary key references auth.users(id) on delete cascade,
  verified_at timestamptz not null default timezone('utc', now()),
  proof_hash text not null unique check (proof_hash ~ '^[0-9a-f]{64}$')
);

comment on table public.verified_users is
  'Privacy-minimal Qyvox age-verification receipts; no DOB or age data.';
comment on column public.verified_users.proof_hash is
  'SHA-256 fingerprint used only to reject an identical proof replay.';

alter table public.verified_users enable row level security;

-- The FastAPI service uses the server-only service-role key. No browser policy
-- is created, so anon/authenticated clients cannot read or mutate receipts.
revoke all on table public.verified_users from anon, authenticated;

