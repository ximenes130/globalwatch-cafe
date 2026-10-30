---
id: "001"
titulo: Fundação, autenticação com Google e deploy
status: em-implementacao
---

# 001 — Fundação, autenticação e deploy: tarefas

Bloco do dia: 8h às 10h. Nada aqui é cortável.

- [x] **T1.1** (P0) Criar repositório privado no GitHub e o primeiro push.
  - _Req: R1.9_
  - Verificação: `git log -p | grep -iE "key|secret"` sem segredos.
- [ ] **T1.2** (P0) Backend mínimo: FastAPI, `config.py`, `/health`, Dockerfile, pyproject.
  - _Req: R1.7_
  - Arquivos: `backend/app/main.py`, `backend/app/config.py`, `backend/Dockerfile`, `backend/pyproject.toml`
  - Verificação: `docker build` e `curl localhost:8000/health`.
- [ ] **T1.3** (P0) Projeto Supabase: provedor Google, migration `001_init.sql` com RLS.
  - _Req: R1.3, R1.10_
  - Arquivos: `supabase/migrations/001_init.sql`
  - Verificação: tabelas e políticas visíveis no painel; select com anon key de outro usuário vazio.
- [ ] **T1.4** (P0) `auth.py` com validação JWKS e rota `GET /me`; testes de 401.
  - _Req: R1.5, R1.6_
  - Arquivos: `backend/app/auth.py`, `backend/tests/test_auth.py`
  - Verificação: `pytest backend/tests/test_auth.py`.
- [ ] **T1.5** (P0) Frontend: Vite + React + TS + Tailwind + shadcn/ui, tela de login, sair, cliente `api.ts`.
  - _Req: R1.1, R1.2, R1.4_
  - Arquivos: `frontend/src/pages/Login.tsx`, `frontend/src/lib/supabase.ts`, `frontend/src/lib/api.ts`
  - Verificação: login local mostra o e-mail vindo de `/me`.
- [ ] **T1.6** (P0) `.env.example` de front e back.
  - _Req: R1.9_
  - Verificação: revisão manual; nenhum valor real.
- [ ] **T1.7** (P0) Deploy: back no Render, front no Vercel, redirects no Supabase e no Google, OAuth "In production".
  - _Req: R1.3, R1.8_
  - Verificação: login em aba anônima com outra conta Google em produção; `/me` responde.
- [ ] **T1.8** (P0) CI: `ci.yml` com ruff, pytest e `npm run build`.
  - _Req: R1.11_
  - Arquivos: `.github/workflows/ci.yml`
  - Verificação: CI verde no push.
