---
id: "005"
titulo: Chat com IA sobre a análise
status: concluido
---

# 005 — Chat com IA: design

## Visão geral

```text
POST /analyses/{id}/chat {message, history}
  ├─ current_user + checa dono da análise (404 se não for)
  ├─ incrementa usage_daily.messages (429 se passar)
  ├─ monta: system prompt + [polygons.png na apresentação] + histórico truncado
  ├─ loop de tool use com Claude (claude-haiku-5-5), ferramentas presas ao analysis_id da rota
  │    cada chamada → ToolOutput(data) ─┬─ tool_result (JSON) → modelo
  │                                     └─ card {kind, data}   → resposta ao front
  └─ salva mensagens e cards (P1) e devolve {reply, cards}
```

## Componentes e arquivos

| Arquivo | Responsabilidade |
| --- | --- |
| `backend/app/routes/chat.py` | Endpoint, limites, persistência |
| `backend/app/chat/prompt.py` | Prompt de sistema e mensagem de apresentação |
| `backend/app/chat/tools.py` | Definição e execução das ferramentas (fechadas sobre `analysis_id` e `user_id`); cada uma devolve o objeto que vira `tool_result` e card |
| `backend/app/chat/client.py` | Chamada à API da Anthropic, timeout, `max_tokens`, loop de tool use, coleta dos cards |
| `frontend/src/components/Chat.tsx` | UI do chat |
| `frontend/src/components/ChatCards.tsx` | Um componente por tipo de card |

## Contratos

- `POST /analyses/{id}/chat` `{"message": "...", "history": [...]}`
  - `message`: até 1.000 caracteres; `null` só na apresentação (histórico vazio).
  - `history`: mensagens de texto anteriores da sessão (`role`, `content`), as 10
    últimas, cada uma até 4.000 caracteres. Os cards não voltam no histórico: se
    precisar de um número de novo, o modelo chama a ferramenta outra vez.
  - Resposta `200`:

```json
{
  "reply": "texto em markdown simples",
  "cards": [
    { "kind": "summary", "data": { "...": "..." } },
    { "kind": "polygon", "data": { "...": "..." } }
  ]
}
```

- `GET /analyses/{id}/chat` → `[{"id", "role", "content", "cards", "created_at"}]` em ordem,
  com os cards de cada resposta *(P1)*; análise alheia → 404.
- Persistência *(P1)*: depois da resposta, a pergunta (se houver) e a resposta com
  os cards entram numa transação só; a apresentação grava só a resposta.

### Ferramentas e o que cada uma devolve

O mesmo objeto `data` vai para o modelo e para o card (R5.11). Unidades no nome do
campo (`_ha`), datas em ISO 8601, áreas arredondadas a 2 casas e índices a 4, como
o processamento já grava. Nenhuma ferramenta recebe `analysis_id` como argumento.

| Ferramenta | `kind` do card | `data` |
| --- | --- | --- |
| `get_analysis_summary()` | `summary` | `filename`, `acquired_at`, `second_acquired_at`, `total_area_ha`, `valid_area_ha`, `masked_area_ha`, `potential_area_ha`, `polygon_count`, `excluded_area_ha` (por nível da cascata), `thresholds` (`ndvi_min`, `ndvi_max`, `min_area_ha` e, com segunda data, `ndvi_amplitude_max`), `method_version` |
| `get_polygon(id: int)` | `polygon` | `id`, `area_ha`, `ndvi_mean`, `gndvi_mean`, `centroid` (`[lon, lat]` em WGS84) |
| `get_limitations()` | `limitations` | `items` (textos de `rationale.limitations`) e `references` (`citation`, `doi`) |

- `get_analysis_summary` lê a linha da análise (`stats`, `params`, `rationale`).
- `get_polygon` lê o `result.geojson` da análise no Storage, depois de conferir o
  dono pela linha; o centróide sai do shapely sobre a geometria em WGS84. O
  GeoJSON é baixado uma vez por requisição, mesmo com várias chamadas.
- `get_limitations` lê `rationale` (R2.18): índice não comprova café, sem
  validação de campo, confusão com mata e eucalipto, resolução de 10 m.

### Do resultado ao modelo e ao card

1. Cada ferramenta devolve `ToolOutput(kind, data)` ou lança `ToolError(mensagem)`.
2. Sucesso: o modelo recebe `{"type": "tool_result", "tool_use_id": …, "content":
   json.dumps(data, ensure_ascii=False)}` e a resposta ganha `{"kind", "data"}`.
3. `ToolError` (ex.: `get_polygon(999)`): o modelo recebe `is_error: true` com a
   mensagem ("Polígono 999 não existe; a análise tem 124 polígonos.") e nenhum
   card é criado (R5.13). O texto do modelo explica a falha.
4. Cards em ordem de primeira chamada, sem repetir `(ferramenta, argumentos)`
   na mesma resposta (R5.12). O `tool_result` repetido vai ao modelo normalmente.
5. Até 4 rodadas de ferramentas por mensagem; na quinta, a chamada sai com
   `tool_choice: none` e o modelo responde com o que já tem (R5.6).
6. Apresentação (R5.1): primeira rodada com `tool_choice` forçando
   `get_analysis_summary`, então o card de resumo sempre acompanha a apresentação;
   as rodadas seguintes voltam a `auto`.

### Prompt de sistema (o que muda por causa dos cards)

- "O usuário vê, ao lado da sua resposta, um card com os dados de cada ferramenta
  que você chamar." O texto interpreta (o que o número significa, por que a área
  foi excluída, o que a limitação implica) e cita só os números que sustentam a
  explicação, sem listar o card de novo.
- Número no texto tem de ser igual ao do `tool_result`, com vírgula decimal; o
  modelo não arredonda de outro jeito nem soma valores que a ferramenta não deu.
- Dado ausente em todas as ferramentas → "não sei"/"o processamento não mede isso".

### Interface

- O chat fica no painel lateral da análise, em abas "Resultado" e "Assistente" (Radix
  Tabs, já instalado), com o mapa sempre visível ao lado; no celular, as abas ficam
  abaixo do mapa. A apresentação é pedida na primeira vez que a aba abre.
- A conversa fica em `chat_messages` (T5.5): o chat abre carregando
  `GET /analyses/{id}/chat` e só pede a apresentação se a conversa estiver vazia.
  O histórico enviado ao modelo continua saindo do front (só o texto das mensagens
  que deram certo); se gravar a conversa falhar, a resposta ainda chega e o erro
  fica no log. Pergunta que falhou não é gravada.
- Markdown simples (parágrafos, listas, negrito e itálico) renderizado por um parser
  pequeno que monta elementos React: sem HTML vindo do modelo e sem dependência nova.
- Erro do assistente (R5.7): a pergunta fica na conversa com a mensagem do backend e
  "Tentar de novo", que reenvia a mesma pergunta.
- Os cards ficam dentro da bolha da resposta, acima do texto (na ordem do que foi
  consultado e depois explicado), com o rótulo "Dados do processamento".
- `summary`: datas (uma ou duas), área potencial em destaque, área total, válida
  e mascarada, nº de polígonos e as exclusões por nível; mesmos rótulos e
  formatação do painel (`lib/format.ts`, spec 004).
- `polygon`: "Área potencial nº {id}", área, NDVI médio, GNDVI médio, centróide;
  "Ver no mapa" *(P1, R5.15)* centraliza e destaca o polígono reutilizando as
  camadas de realce do `MapView`.
- `limitations`: lista curta, recolhida a partir do 4º item, com as referências
  (DOI como link).
- Tudo renderizado como texto pelo React; nenhum campo do card é interpretado
  como HTML ou markdown.

## Decisões

| Decisão | Alternativa recusada | Motivo |
| --- | --- | --- |
| Tool use | Colar o JSON inteiro no prompt | Números exatos sob demanda; fica claro de onde vem cada valor |
| Claude Haiku 5.5 | Modelo maior; modelo open source hospedado | Barato, aceita imagem e ferramentas; open source não cabe no free com GPU |
| Ferramentas sem `analysis_id` | Id como argumento | Fecha o vetor de prompt injection entre análises |
| Card = retorno da ferramenta, montado no backend | Modelo escreve o card (JSON ou markdown) | O card é a prova de que o número veio do processamento (C2.1); se o modelo errar no texto, o card mostra o valor certo ao lado |
| Mesmo objeto para modelo e card | Resumo em texto para o modelo e objeto para o card | Um único arredondamento: o número citado é o mesmo que aparece no card |
| Cards fora do histórico enviado ao modelo | Reenviar `tool_use`/`tool_result` antigos | Histórico menor e sem montar pares de ferramenta; chamar a ferramenta de novo custa pouco |
| Cards acima do texto | Cards depois do texto | Segue a ordem real: primeiro a consulta, depois a explicação |
| `polygons.png` na apresentação | `classification.png` | O PNG da classificação é transparente fora da área potencial: sem a paisagem, a IA não tem o que descrever. O `polygons.png` traz a cor verdadeira e o número de cada polígono, o mesmo de `get_polygon`; números continuam só pelas ferramentas |

Fallback se o tempo apertar: versão sem ferramentas que recebe o resumo da
análise no prompt de sistema (ainda cumpre C2.1, pois o resumo vem do banco); a
resposta leva um único card `summary` montado pelo backend com o mesmo resumo.

## Riscos

- Custo/abuso → `max_tokens` baixo, 4 rodadas de ferramenta, 30 mensagens/dia,
  teto de gasto no console da Anthropic.
- Modelo inventa número → prompt + teste com perguntas armadilha; o card ao lado
  expõe a diferença.
- Texto repete o card inteiro → regra do prompt e conferência manual na T5.2.

## Estratégia de testes

| Requisito | Teste |
| --- | --- |
| R5.2 | `test_chat_tools.py`: `data` do resumo e do polígono iguais a `GET /analyses/{id}` e ao GeoJSON; com segunda data, `second_acquired_at` e `ndvi_amplitude_max` presentes |
| R5.5 | `test_chat.py`: usuário B no chat da análise de A → 404; `test_chat_tools.py`: nenhuma ferramenta aceita id de análise |
| R5.10, R5.11 | `test_chat.py` com cliente mockado: o `tool_result` enviado ao modelo é o JSON do `data` do card; um texto do modelo com número inventado não altera o card |
| R5.12 | `test_chat.py`: duas chamadas iguais → um card; chamadas a polígonos diferentes → dois |
| R5.13 | `test_chat.py`: `get_polygon(999)` → `is_error` ao modelo e nenhum card |
| R5.1 | `test_chat.py`: apresentação força `get_analysis_summary` e devolve o card `summary` |
| R5.4 | Manual: "qual a acurácia?" e "quanto é 90% de confiança?" não geram percentual |
| R5.6 | `test_chat.py`: na 5ª rodada a chamada sai com `tool_choice: none`; `test_ratelimit.py` (006) |
| R5.7 | Teste com cliente mockado lançando timeout |
| R5.14 | Manual em 375 px e desktop: cards com os mesmos valores do painel; card com `<b>` no nome do arquivo aparece como texto |
| R5.15 | Manual: "Ver no mapa" no polígono do card leva ao polígono com o mesmo id do popup |
