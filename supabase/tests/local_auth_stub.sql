-- Simula o mínimo do Supabase num Postgres puro, só para testes locais.
-- Não aplicar no Supabase.

create role anon nologin;
create role authenticated nologin;
create role service_role nologin bypassrls;

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
