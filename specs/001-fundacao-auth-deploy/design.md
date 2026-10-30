---
id: "001"
titulo: Fundação, autenticação com Google e deploy
status: concluido
---

# 001 — Fundação, autenticação e deploy: design

## Visão geral

```text
Navegador (SPA estática no Render, CDN) ──(Supabase JS: OAuth Google)──> Supabase Auth ──> JWT
   │
   └──(Authorization: Bearer <jwt>)──> FastAPI (Render, Docker)
                                         ├─ valida JWT via JWKS do Supabase
                                         ├─ Postgres (service role + filtro user_id)
                                         └─ Storage privado
```

## Componentes e arquivos

| Arquivo | Responsabilidade |
| --- | --- |
| `backend/app/main.py` | App FastAPI, CORS, rotas, `/health` |
| `backend/app/config.py` | Settings via env (pydantic-settings) |
| `backend/app/auth.py` | Dependência `current_user`: busca e cacheia JWKS, valida token, devolve `user_id` |
| `backend/app/db.py` | Cliente Postgres/Supabase com service role |
| `backend/Dockerfile`, `backend/pyproject.toml` | Imagem e dependências (GDAL via wheel do rasterio) |
| `frontend/` | Vite + React + TypeScript + Tailwind + shadcn/ui |
| `frontend/src/lib/supabase.ts` | Cliente Supabase (URL e anon key públicas) |
| `frontend/src/lib/api.ts` | `fetch` com o JWT da sessão; trata 401 voltando ao login |
| `frontend/src/pages/Login.tsx` | Tela de login |
| `supabase/migrations/001_init.sql` | Tabelas e RLS |
| `.github/workflows/ci.yml` | Lint, testes, build |
| `render.yaml` | Blueprint: `globalwatch-cafe` (Static Site) e `globalwatch-cafe-api` (Web Service Docker) |

## Contratos

- `GET /health` → `200 {"status":"ok","db":"ok"}` (público). `db` vale
  `"error"` se o `select 1` falhar e `"not_configured"` sem `DATABASE_URL`.
  Responde sempre 200: é o health check do Render, e um 503 por falha do banco
  reiniciaria o serviço sem resolver nada. O keepalive (T7.1) confere `db`.
- Conexão: `DATABASE_URL` aponta para o pooler do Supabase (Supavisor), porque
  a conexão direta é só IPv6 e o Render free não tem IPv6. No modo transação
  (porta 6543), prepared statements ficam desligados.
- `GET /me` → `200 {"user_id": "...", "email": "..."}` (protegido; prova a
  validação do JWT ponta a ponta).
- Validação do JWT (`auth.py`): chave pública do JWKS
  (`<SUPABASE_URL>/auth/v1/.well-known/jwks.json`, o projeto usa ES256),
  cache de 10 min; aceita só ES256/RS256 (bloqueia confusão com HS256); exige
  `exp`, `iss` (`<SUPABASE_URL>/auth/v1`), `aud` e `sub`; recusa sessão
  anônima (`is_anonymous`), pois só há login com Google. Falha → 401 com
  `WWW-Authenticate: Bearer`; JWKS inacessível ou `SUPABASE_URL` ausente → 503.

### Modelo de dados (`001_init.sql`)

- `analyses`: `id uuid pk`, `user_id uuid not null`, `created_at`, `status`,
  `filename`, `acquired_at`, `crs`, `bounds_wgs84 jsonb`, `stats jsonb`,
  `params jsonb`, `method_version text`, `error text`.
- `chat_messages`: `id`, `analysis_id fk on delete cascade`, `user_id`, `role`,
  `content`, `created_at`.
- `usage_daily`: `user_id`, `day date`, `uploads int`, `messages int`, pk
  `(user_id, day)`.
- `user_id` referencia `auth.users(id) on delete cascade`; `status` restrito a
  `processing`, `completed`, `failed`; `role` a `user`, `assistant`.
- RLS ligada nas três, com política **só de leitura** para `authenticated`
  (`user_id = auth.uid()`). `anon` não tem acesso. Toda escrita passa pelo
  backend (service role): se o usuário pudesse escrever com a anon key,
  zeraria o próprio `usage_daily` (fura R6.8/R6.9) ou alteraria `stats` (fere
  C2). O backend **também** filtra por `user_id` (ver 006).
- Teste de isolamento em `supabase/tests/rls_isolation.sql`: roda numa
  transação com `rollback`, no Postgres local (com o stub
  `supabase/tests/local_auth_stub.sql`) e no Supabase.

### Variáveis de ambiente

- Back: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_AUDIENCE`
  (`authenticated`), `ANTHROPIC_API_KEY`, `CORS_ORIGINS`, `DATABASE_URL`.
- Front: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_URL`.

## Decisões

| Decisão | Alternativa recusada | Motivo |
| --- | --- | --- |
| Supabase (Auth + Postgres + Storage) | Firebase; Auth0 + Neon + R2 | Um serviço resolve login, RLS e storage privado no plano free |
| Vite + React | Next.js | Mais rápido de montar e publicar num dia; SPA basta |
| Render (Docker) | Fly.io; HF Spaces | Free sem cartão, deploy pelo GitHub; HF Spaces fica de plano B (mais RAM) |
| Front como Static Site no Render | Vercel; servir o front pelo FastAPI | Um Blueprint e um provedor a menos para configurar e documentar (R7.2); static site não hiberna, então a tela de "acordando o servidor" aparece na hora. Servir pelo FastAPI prenderia a página ao cold start da API |
| Validar JWT por JWKS | Chamar `auth.getUser` a cada request | Sem ida à rede por request; valida assinatura localmente |

### Execução local (`compose.yaml`)

- `api`: imagem do `backend/Dockerfile`, `backend/app` montado e
  `uvicorn --reload`; lê `backend/.env`. Health check em `/health`.
- `web`: `node:24-alpine` com `frontend/` montado, `npm ci` e `vite --host`;
  `node_modules` em volume próprio (binários nativos do container não se
  misturam com os do host). O Vite lê `frontend/.env.local`.
- Banco e auth: o Supabase real, pois o login Google passa por ele.
- Perfil `test`: `db-test` (Postgres 17 em tmpfs) e `rls-test`, que roda
  `supabase/tests/run.sh` (stub + migrations + `rls_isolation.sql` num banco
  recriado a cada execução). O CI usa o mesmo script.

## Riscos

- OAuth em modo "Testing" bloqueia o avaliador → publicar a tela de
  consentimento (R1.3) e testar em aba anônima com outra conta.
- Redirects errados no Supabase/Google → cadastrar a URL de produção do front
  nos dois.
- Render dorme após ~15 min → front mostra "acordando o servidor" (spec 004).
- Front e API em subdomínios diferentes do `onrender.com` → CORS restrito à
  origem do front (`CORS_ORIGINS`).
- Rebuild do static site com variável `VITE_*` errada publica front quebrado →
  conferir as variáveis antes do primeiro deploy; `VITE_*` entram no build.

## Estratégia de testes

| Requisito | Teste |
| --- | --- |
| R1.5, R1.6 | `tests/test_auth.py`: token válido (chave de teste), ausente, expirado, `aud` errado → 401 |
| R1.7 | `tests/test_health.py` + `curl` em produção |
| R1.2, R1.3, R1.4 | Manual em produção, aba anônima, conta Google diferente |
| R1.10 | Aplicar migration no Supabase; consulta com anon key de outro usuário retorna vazio |
| R1.11 | CI verde no GitHub |
