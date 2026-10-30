---
id: "005"
titulo: Chat com IA sobre a análise
status: aprovado
desafio: [5]
pontos: Chatbot e coerência dos resultados (10)
prioridade: P0 (versão mínima e cards) / P1 (histórico persistido, card ligado ao mapa)
---

# 005 — Chat com IA: requisitos

## Objetivo

Um assistente que apresenta a imagem classificada e responde perguntas sobre os
resultados e suas limitações, usando apenas números e geometrias vindos do
processamento. Cada consulta que a IA faz ao processamento serve a dois leitores: o
modelo, que recebe os dados para explicar o que foi encontrado, e o usuário, que vê
os mesmos dados num card ao lado da resposta e pode conferir o texto contra eles.

## Histórias

- **H5.1** Como usuário, quero que o assistente me apresente o resultado da
  análise, para entender rapidamente o que foi encontrado.
- **H5.2** Como usuário, quero perguntar sobre áreas, polígonos e confiança,
  para tirar dúvidas sem ler a documentação técnica.
- **H5.3** Como usuário, quero ver os dados que a IA consultou para responder,
  para conferir que os números do texto vêm do processamento e não da IA.

## Critérios de aceite (EARS)

### Conversa

- **R5.1** — QUANDO o usuário abrir o chat de uma análise pela primeira vez, O
  SISTEMA DEVE enviar ao modelo o PNG da classificação e devolver uma
  apresentação da imagem e do resultado, acompanhada do card de resumo (R5.10).
- **R5.2** — O modelo DEVE obter números e geometrias apenas por ferramentas
  do backend: `get_analysis_summary`, `get_polygon(id)` e
  `get_limitations`, que leem só a análise da rota, depois de conferir o dono.
  Quando a análise tiver segunda data (spec 003), `get_analysis_summary` DEVE
  incluir a data dela, o limite de amplitude e a área excluída por amplitude.
- **R5.3** — O SISTEMA DEVE instruir o modelo a responder em português, chamar
  o resultado de "área potencial", citar só números das ferramentas, dizer
  que não sabe quando o dado não existir e lembrar que o usuário vê os cards:
  o texto interpreta os dados, não repete todos e nunca os contradiz.
- **R5.4** — QUANDO o usuário perguntar sobre confiança ou acurácia, O SISTEMA
  DEVE responder com as limitações do método e não inventar percentuais
  (C1.2).
- **R5.5** — O `analysis_id` DEVE vir da rota e ser checado contra o dono; o
  texto do usuário não altera ferramentas, ids nem o prompt de sistema.
- **R5.6** — O SISTEMA DEVE limitar `max_tokens`, truncar o histórico enviado
  ao modelo, limitar as rodadas de ferramenta por mensagem e aplicar o limite
  diário de mensagens (R6.9).
- **R5.7** — SE a API do modelo falhar ou exceder o tempo, ENTÃO O SISTEMA DEVE
  mostrar erro compreensível e permitir reenviar.
- **R5.8** — A interface do chat DEVE mostrar indicador de digitação, mensagens
  em markdown simples e sugestões de perguntas iniciais.
- **R5.9** *(P1)* — O SISTEMA DEVE persistir o histórico em `chat_messages`,
  com os cards de cada resposta; se cortado, o histórico vive só na sessão do
  navegador.

### Resultado das ferramentas: contexto para o modelo e card para o usuário

- **R5.10** — QUANDO o modelo chamar uma ferramenta, O SISTEMA DEVE devolver o
  resultado ao modelo como `tool_result` em JSON e anexar à resposta um card
  com esse mesmo resultado, na ordem em que as ferramentas foram chamadas.
- **R5.11** — O card DEVE ser montado no backend a partir do retorno da
  ferramenta, nunca do texto do modelo; o modelo e o card recebem o mesmo
  objeto, com o mesmo arredondamento (área em ha com 2 casas, índices com 4).
- **R5.12** — QUANDO a mesma ferramenta for chamada com os mesmos argumentos
  mais de uma vez na mesma resposta, O SISTEMA DEVE mostrar um card só.
- **R5.13** — SE uma ferramenta falhar (por exemplo, polígono inexistente),
  ENTÃO O SISTEMA DEVE avisar o modelo com `is_error` e uma mensagem curta, e
  não gerar card.
- **R5.14** — A interface DEVE mostrar os cards junto da resposta que os usou,
  identificados como dados do processamento, formatados como no painel da
  análise (spec 004) e com o texto escapado (nada do card vira HTML).
- **R5.15** *(P1)* — QUANDO o usuário acionar "Ver no mapa" num card de
  polígono, O SISTEMA DEVE centralizar o mapa no polígono e destacá-lo.

## Fora de escopo

- Chat global sem análise selecionada.
- Streaming de resposta (só se sobrar tempo).
- Card gerado pelo modelo (layout ou números escolhidos pela IA).
- Ferramentas novas além das três (por exemplo, listar os maiores polígonos).

## Questões resolvidas

- Segunda data (spec 003, R3.10): `get_analysis_summary` expõe
  `second_acquired_at`, o limite `ndvi_amplitude_max` e a área do passo N3c
  (R5.2); o card de resumo mostra as duas datas, como o painel.
