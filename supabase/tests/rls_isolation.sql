-- Teste de isolamento da RLS (R1.10, C3.2). Tudo roda numa transação com
-- rollback: seguro no Postgres local e no Supabase.
-- Uso: psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f supabase/tests/rls_isolation.sql

begin;

insert into auth.users (id, email) values
  ('00000000-0000-0000-0000-00000000000a', 'rls-test-a@example.com'),
  ('00000000-0000-0000-0000-00000000000b', 'rls-test-b@example.com');

insert into public.analyses (id, user_id, filename) values
  ('10000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-00000000000a', 'a.tif'),
  ('10000000-0000-0000-0000-00000000000b', '00000000-0000-0000-0000-00000000000b', 'b.tif');

insert into public.chat_messages (analysis_id, user_id, role, content) values
  ('10000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-00000000000a', 'user', 'oi'),
  ('10000000-0000-0000-0000-00000000000b', '00000000-0000-0000-0000-00000000000b', 'user', 'oi');

insert into public.usage_daily (user_id, uploads) values
  ('00000000-0000-0000-0000-00000000000a', 5),
  ('00000000-0000-0000-0000-00000000000b', 1);

-- Usuário A autenticado.
set local role authenticated;
set local request.jwt.claims = '{"sub":"00000000-0000-0000-0000-00000000000a","role":"authenticated"}';

do $$
begin
  if (select count(*) from public.analyses) <> 1
     or exists (select 1 from public.analyses where user_id <> auth.uid()) then
    raise exception 'FALHA: A vê análises de outro usuário';
  end if;
  if (select count(*) from public.chat_messages) <> 1 then
    raise exception 'FALHA: A vê mensagens de outro usuário';
  end if;
  if (select count(*) from public.usage_daily) <> 1 then
    raise exception 'FALHA: A vê o uso de outro usuário';
  end if;
end $$;

-- A não pode escrever: zerar o próprio contador furaria o limite diário.
do $$
begin
  begin
    update public.usage_daily set uploads = 0;
    raise exception 'FALHA: A conseguiu alterar usage_daily';
  exception when insufficient_privilege then null;
  end;
  begin
    insert into public.analyses (user_id, filename) values (auth.uid(), 'x.tif');
    raise exception 'FALHA: A conseguiu inserir análise';
  exception when insufficient_privilege then null;
  end;
  begin
    delete from public.analyses;
    raise exception 'FALHA: A conseguiu apagar análises';
  exception when insufficient_privilege then null;
  end;
end $$;

-- Sem login (anon): nenhum acesso.
reset role;
set local role anon;
set local request.jwt.claims = '{"role":"anon"}';

do $$
begin
  begin
    perform 1 from public.analyses;
    raise exception 'FALHA: anon leu analyses';
  exception when insufficient_privilege then null;
  end;
end $$;

reset role;
select 'OK: isolamento da RLS verificado' as resultado;

rollback;
