---
id: "006"
titulo: Segurança, isolamento e limites de uso
status: em-implementacao
---

# 006 — Segurança e limites: tarefas

Bloco do dia: 18h às 19h (validação e auth entram antes, junto de 001 e 002).
Corte se estourar: retenção automática (fica documentada).

- [x] **T6.1** (P0) Validação de upload completa e testes.
  - _Req: R6.5, R6.6, R6.7_
  - Arquivos: `backend/app/validation.py`, `backend/tests/test_upload.py`
  - Verificação: `pytest backend/tests/test_upload.py`.
- [x] **T6.2** (P0) Isolamento: filtro por `user_id`, 404 para recurso alheio, storage privado e DELETE completo.
  - _Req: R6.2, R6.3, R6.4, R6.14_
  - Arquivos: `backend/app/routes/analyses.py`, `backend/app/storage.py`, `backend/tests/test_isolation.py`
  - Verificação: `pytest backend/tests/test_isolation.py` (matriz de rotas tirada do OpenAPI do app).
- [ ] **T6.3** (P0) Teste que garante JWT em todas as rotas.
  - _Req: R6.1_
  - Arquivos: `backend/tests/test_auth.py`
  - Verificação: `pytest backend/tests/test_auth.py`.
- [x] **T6.4** (P0) Limites diários de upload e chat.
  - _Req: R6.8, R6.9_
  - Arquivos: `backend/app/ratelimit.py`, `backend/tests/test_ratelimit.py`
  - Verificação: `pytest backend/tests/test_ratelimit.py`.
- [ ] **T6.5** (P0) CORS restrito, handler de erros neutro.
  - _Req: R6.10, R6.12_
  - Arquivos: `backend/app/main.py`, `backend/app/errors.py`, `backend/tests/test_errors.py`
  - Verificação: `pytest backend/tests/test_errors.py` + `curl` com Origin estranha.
- [ ] **T6.6** (P0) Auditoria de segredos e teto de gasto da Anthropic.
  - _Req: R6.11, R6.13_
  - Verificação: grep no histórico e no bundle; print do teto (sem a chave) em `docs/evidencias/`.
- [ ] **T6.7** (P1) Retenção de 7 dias automatizada.
  - _Req: R6.15_
  - Arquivos: `.github/workflows/retention.yml`
  - Verificação: análise com `created_at` antigo é removida.
