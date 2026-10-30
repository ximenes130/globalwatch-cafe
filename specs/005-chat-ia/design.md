---
id: "005"
titulo: Chat com IA sobre a análise
status: rascunho
---

# 005 — Chat com IA: design

## Visão geral

```text
POST /analyses/{id}/chat {mensagem}
  ├─ current_user + checa dono da análise (404 se não for)
  ├─ incrementa usage_daily.messages (429 se passar)
  ├─ monta: system prompt + [PNG da classificação na 1ª mensagem] + histórico truncado
  ├─ loop de tool use com Claude (claude-haiku-5-5), ferramentas presas ao analysis_id da rota
  └─ salva mensagens (P1) e devolve resposta
```

## Componentes e arquivos

| Arquivo | Responsabilidade |
| --- | --- |
| `backend/app/routes/chat.py` | Endpoint, limites, persistência |
| `backend/app/chat/prompt.py` | Prompt de sistema e mensagem de apresentação |
| `backend/app/chat/ferramentas.py` | Definição e execução das ferramentas (fechadas sobre `analysis_id` e `user_id`) |
| `backend/app/chat/cliente.py` | Chamada à API da Anthropic, timeout, `max_tokens` |
| `frontend/src/components/Chat.tsx` | UI do chat |

## Contratos

- `POST /analyses/{id}/chat` `{"mensagem": "..."}` (máx. 1.000 caracteres)
  → `200 {"resposta": "...", "ferramentas_usadas": ["..."]}`.
- `GET /analyses/{id}/chat` → histórico *(P1)*.

### Ferramentas

- `obter_resumo_analise()` → data, área total, área válida, área potencial,
  nº de polígonos, `params`, `method_version`.
- `obter_poligono(id: int)` → `area_ha`, `ndvi_medio`, centróide; erro se não
  existir.
- `obter_limitacoes()` → lista fixa derivada da justificativa (R2.18):
  índice não comprova café, sem validação de campo, uma data só, confusão com
  mata/eucalipto, resolução de 10 m.

Nenhuma ferramenta recebe `analysis_id` como argumento.

## Decisões

| Decisão | Alternativa recusada | Motivo |
| --- | --- | --- |
| Tool use | Colar o JSON inteiro no prompt | Números exatos sob demanda; fica claro de onde vem cada valor |
| Claude Haiku 5.5 | Modelo maior; modelo open source hospedado | Barato, aceita imagem e ferramentas; open source não cabe no free com GPU |
| Ferramentas sem `analysis_id` | Id como argumento | Fecha o vetor de prompt injection entre análises |

Fallback se o tempo apertar: versão sem ferramentas que recebe o resumo da
análise no prompt de sistema (ainda cumpre C2.1, pois o resumo vem do banco).

## Riscos

- Custo/abuso → `max_tokens` baixo, 30 mensagens/dia, teto de gasto no
  console da Anthropic.
- Modelo inventa número → prompt + teste com perguntas armadilha.

## Estratégia de testes

| Requisito | Teste |
| --- | --- |
| R5.2 | `test_chat_ferramentas.py`: ferramenta devolve os mesmos números de `GET /analyses/{id}` |
| R5.5 | `test_chat_ferramentas.py`: usuário B no chat da análise de A → 404 |
| R5.4 | Manual: "qual a acurácia?" e "quanto é 90% de confiança?" não geram percentual |
| R5.6 | `test_ratelimit.py` (006) |
| R5.7 | Teste com cliente mockado lançando timeout |
