-- Simula o mínimo do Supabase num Postgres puro, só para testes locais.
-- Não aplicar no Supabase.

-- Papéis valem para o cluster inteiro: só cria se ainda não existirem.
do $$
begin
  if not exists (select from pg_roles where rolname = 'anon') then
    create role anon nologin;
  end if;
  if not exists (select from pg_roles where rolname = 'authenticated') then
    create role authenticated nologin;
  end if;
  if not exists (select from pg_roles where rolname = 'service_role') then
    create role service_role nologin bypassrls;
  end if;
end $$;

create schema auth;
grant usage on schema auth to anon, authenticated, service_role;
grant usage on schema public to anon, authenticated, service_role;

create table auth.users (id uuid primary key, email text);

-- Mesma fonte que o Supabase usa: o claim `sub` do JWT da requisição.
create function auth.uid() returns uuid language sql stable as $$
  select nullif(current_setting('request.jwt.claims', true)::jsonb ->> 'sub', '')::uuid
$$;

-- Equivalente aos privilégios padrão do Supabase, que a migration precisa revogar.
alter default privileges in schema public grant all on tables to anon, authenticated, service_role;

-- Mínimo de `storage.buckets` para a migration do bucket rodar fora do Supabase.
create schema storage;
create table storage.buckets (
  id text primary key,
  name text not null,
  public boolean default false,
  file_size_limit bigint,
  allowed_mime_types text[]
);
