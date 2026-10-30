---
id: "001"
titulo: Fundação, autenticação com Google e deploy
status: rascunho
---

# 001 — Fundação, autenticação e deploy: design

## Visão geral

```text
Navegador ──(Supabase JS: OAuth Google)──> Supabase Auth ──> JWT
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

## Contratos

- `GET /health` → `200 {"status":"ok","db":"ok"}` (público).
- `GET /me` → `200 {"user_id": "...", "email": "..."}` (protegido; prova a
  validação do JWT ponta a ponta).

### Modelo de dados (`001_init.sql`)

- `analyses`: `id uuid pk`, `user_id uuid not null`, `created_at`, `status`,
  `filename`, `acquired_at`, `crs`, `bounds_wgs84 jsonb`, `stats jsonb`,
  `params jsonb`, `method_version text`, `error text`.
- `chat_messages`: `id`, `analysis_id fk on delete cascade`, `user_id`, `role`,
  `content`, `created_at`.
- `usage_daily`: `user_id`, `day date`, `uploads int`, `messages int`, pk
  `(user_id, day)`.
- RLS ligada nas três, política `user_id = auth.uid()`. O backend usa service
  role e **também** filtra por `user_id` (ver 006).

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
| Validar JWT por JWKS | Chamar `auth.getUser` a cada request | Sem ida à rede por request; valida assinatura localmente |

## Riscos

- OAuth em modo "Testing" bloqueia o avaliador → publicar a tela de
  consentimento (R1.3) e testar em aba anônima com outra conta.
- Redirects errados no Supabase/Google → cadastrar a URL de produção do front
  nos dois.
- Render dorme após ~15 min → front mostra "acordando o servidor" (spec 004).

## Estratégia de testes

| Requisito | Teste |
| --- | --- |
| R1.5, R1.6 | `tests/test_auth.py`: token válido (chave de teste), ausente, expirado, `aud` errado → 401 |
| R1.7 | `tests/test_health.py` + `curl` em produção |
| R1.2, R1.3, R1.4 | Manual em produção, aba anônima, conta Google diferente |
| R1.10 | Aplicar migration no Supabase; consulta com anon key de outro usuário retorna vazio |
| R1.11 | CI verde no GitHub |
