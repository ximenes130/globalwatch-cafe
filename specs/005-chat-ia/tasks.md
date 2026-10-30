---
id: "005"
titulo: Chat com IA sobre a análise
status: rascunho
---

# 005 — Chat com IA: tarefas

Bloco do dia: 16h30 às 18h. Corte se estourar: histórico persistido (fica na sessão).
Se às 18h não estiver de pé: fallback sem ferramentas (ver design).

- [ ] **T5.1** (P0) Ferramentas fechadas sobre `analysis_id`/`user_id` e testes.
  - _Req: R5.2, R5.5_
  - Arquivos: `backend/app/chat/ferramentas.py`, `backend/tests/test_chat_ferramentas.py`
  - Verificação: `pytest backend/tests/test_chat_ferramentas.py`.
- [ ] **T5.2** (P0) Prompt de sistema e apresentação com imagem.
  - _Req: R5.1, R5.3, R5.4_
  - Arquivos: `backend/app/chat/prompt.py`
  - Verificação: manual com perguntas armadilha; registro em `docs/evidencias/chat.md`.
- [ ] **T5.3** (P0) Cliente da API, loop de tool use, limites e erros.
  - _Req: R5.6, R5.7_
  - Arquivos: `backend/app/chat/cliente.py`, `backend/app/routes/chat.py`
  - Verificação: timeout mockado devolve erro tratado.
- [ ] **T5.4** (P0) UI do chat.
  - _Req: R5.8_
  - Arquivos: `frontend/src/components/Chat.tsx`
  - Verificação: manual em 375 px e desktop.
- [ ] **T5.5** (P1) Persistência do histórico.
  - _Req: R5.9_
  - Verificação: recarregar a página mantém a conversa.
