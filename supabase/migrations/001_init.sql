-- Tabelas base com RLS (specs/001-fundacao-auth-deploy, R1.10).
-- Escrita só pelo backend (service role); o usuário autenticado lê apenas as
-- próprias linhas. Motivo no design.md da spec 001.

create table public.analyses (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  created_at timestamptz not null default now(),
  status text not null default 'processing'
    check (status in ('processing', 'completed', 'failed')),
  filename text not null,
  acquired_at timestamptz,
  crs text,
  bounds_wgs84 jsonb,
  stats jsonb,
  params jsonb,
  method_version text,
  error text
);

create index analyses_user_id_created_at_idx on public.analyses (user_id, created_at desc);

create table public.chat_messages (
  id bigint generated always as identity primary key,
  analysis_id uuid not null references public.analyses (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  created_at timestamptz not null default now()
);

create index chat_messages_analysis_id_created_at_idx
  on public.chat_messages (analysis_id, created_at);

create table public.usage_daily (
  user_id uuid not null references auth.users (id) on delete cascade,
  day date not null default current_date,
  uploads integer not null default 0 check (uploads >= 0),
  messages integer not null default 0 check (messages >= 0),
  primary key (user_id, day)
);

alter table public.analyses enable row level security;
alter table public.chat_messages enable row level security;
alter table public.usage_daily enable row level security;

-- O Supabase concede tudo a anon e authenticated por padrão; reduzimos a leitura.
revoke all on public.analyses, public.chat_messages, public.usage_daily from anon, authenticated;
grant select on public.analyses, public.chat_messages, public.usage_daily to authenticated;

-- `(select auth.uid())` é avaliado uma vez por consulta, não por linha.
create policy analyses_select_own on public.analyses
  for select to authenticated using (user_id = (select auth.uid()));

create policy chat_messages_select_own on public.chat_messages
  for select to authenticated using (user_id = (select auth.uid()));

create policy usage_daily_select_own on public.usage_daily
  for select to authenticated using (user_id = (select auth.uid()));
