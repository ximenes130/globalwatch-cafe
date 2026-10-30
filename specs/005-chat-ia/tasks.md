---
id: "005"
titulo: Chat com IA sobre a análise
status: em-implementacao
---

# 005 — Chat com IA: tarefas

Bloco do dia: 16h30 às 18h. Corte se estourar: histórico persistido (fica na sessão)
e "Ver no mapa". Se às 18h não estiver de pé: fallback sem ferramentas (ver design).

- [x] **T5.1** (P0) Ferramentas fechadas sobre `analysis_id`/`user_id`, devolvendo
  `ToolOutput(kind, data)` ou `ToolError`, e testes.
  - _Req: R5.2, R5.5, R5.11, R5.13_
  - Arquivos: `backend/app/chat/tools.py`, `backend/tests/test_chat_tools.py`
  - Verificação: `pytest backend/tests/test_chat_tools.py` (dados iguais à API e ao
    GeoJSON, segunda data presente, polígono inexistente vira `ToolError`, nenhuma
    ferramenta aceita id de análise). A conferência do dono é da rota: o 404 para
    análise alheia é testado na T5.3.
- [x] **T5.2** (P0) Prompt de sistema e apresentação com imagem.
  - _Req: R5.1, R5.3, R5.4_
  - Arquivos: `backend/app/chat/prompt.py`
  - Verificação: manual com perguntas armadilha; o texto cita números iguais aos
    cards e não repete o card inteiro; registro em `docs/evidencias/chat.md`.
- [x] **T5.3** (P0) Cliente da API, loop de tool use com coleta de cards, limites e erros.
  - _Req: R5.1, R5.6, R5.7, R5.10, R5.11, R5.12, R5.13_
  - Arquivos: `backend/app/chat/client.py`, `backend/app/routes/chat.py`,
    `backend/tests/test_chat.py`
  - Verificação: `pytest backend/tests/test_chat.py` com cliente mockado
    (`tool_result` igual ao card, cards sem repetição e na ordem, `is_error` sem
    card, apresentação forçando o resumo, `tool_choice: none` na 5ª rodada,
    timeout devolve erro tratado, análise alheia → 404).
- [x] **T5.4** (P0) UI do chat com os cards.
  - _Req: R5.8, R5.14_
  - Arquivos: `frontend/src/components/Chat.tsx`, `frontend/src/components/ChatCards.tsx`,
    `frontend/src/lib/api.ts`
  - Verificação: manual em 375 px e desktop; valores dos cards iguais aos do painel;
    nome de arquivo com HTML aparece como texto.
- [ ] **T5.5** (P1) Persistência do histórico com os cards.
  - _Req: R5.9_
  - Arquivos: `supabase/migrations/` (coluna `cards jsonb` em `chat_messages`),
    `backend/app/routes/chat.py`
  - Verificação: recarregar a página mantém a conversa e os cards.
- [x] **T5.6** (P1) "Ver no mapa" no card de polígono.
  - _Req: R5.15_
  - Arquivos: `frontend/src/components/ChatCards.tsx`, `frontend/src/components/MapView.tsx`
  - Verificação: manual; o polígono destacado tem o mesmo id do card e do popup.
