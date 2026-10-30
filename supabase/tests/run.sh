#!/bin/sh
# Recria um banco descartável e aplica stub, migrations e teste de RLS.
# Só para Postgres puro (local, compose, CI); no Supabase, rode a migration e
# o rls_isolation.sql diretamente. Conexão pelas variáveis PG* do libpq.
set -eu
export PGOPTIONS="-c client_min_messages=warning"

tests_dir=$(dirname "$0")
psql_strict="psql -v ON_ERROR_STOP=1 -q"

dropdb --if-exists rls_test
createdb rls_test
export PGDATABASE=rls_test

$psql_strict -f "$tests_dir/local_auth_stub.sql"
for migration in "$tests_dir"/../migrations/*.sql; do
  $psql_strict --single-transaction -f "$migration"
done
$psql_strict -f "$tests_dir/rls_isolation.sql"
