---
id: "005"
titulo: Chat com IA sobre a análise
status: rascunho
desafio: [5]
pontos: Chatbot e coerência dos resultados (10)
prioridade: P0 (versão mínima) / P1 (histórico persistido)
---

# 005 — Chat com IA: requisitos

## Objetivo

Um assistente que apresenta a imagem classificada e responde perguntas sobre os
resultados e suas limitações, usando apenas números e geometrias vindos do
processamento.

## Histórias

- **H5.1** Como usuário, quero que o assistente me apresente o resultado da
  análise, para entender rapidamente o que foi encontrado.
- **H5.2** Como usuário, quero perguntar sobre áreas, polígonos e confiança,
  para tirar dúvidas sem ler a documentação técnica.

## Critérios de aceite (EARS)

- **R5.1** — QUANDO o usuário abrir o chat de uma análise pela primeira vez, O
  SISTEMA DEVE enviar ao modelo o PNG da classificação e devolver uma
  apresentação da imagem e do resultado.
- **R5.2** — O modelo DEVE obter números e geometrias apenas por ferramentas
  do backend: `get_analysis_summary`, `get_polygon(id)` e
  `get_limitations`, que leem do banco filtrando por `user_id`.
- **R5.3** — O SISTEMA DEVE instruir o modelo a responder em português, chamar
  o resultado de "área potencial", citar só números das ferramentas e dizer
  que não sabe quando o dado não existir.
- **R5.4** — QUANDO o usuário perguntar sobre confiança ou acurácia, O SISTEMA
  DEVE responder com as limitações do método e não inventar percentuais
  (C1.2).
- **R5.5** — O `analysis_id` DEVE vir da rota e ser checado contra o dono; o
  texto do usuário não altera ferramentas, ids nem o prompt de sistema.
- **R5.6** — O SISTEMA DEVE limitar `max_tokens`, truncar o histórico enviado
  ao modelo e aplicar o limite diário de mensagens (R6.9).
- **R5.7** — SE a API do modelo falhar ou exceder o tempo, ENTÃO O SISTEMA DEVE
  mostrar erro compreensível e permitir reenviar.
- **R5.8** — A interface do chat DEVE mostrar indicador de digitação, mensagens
  em markdown simples e sugestões de perguntas iniciais.
- **R5.9** *(P1)* — O SISTEMA DEVE persistir o histórico em `chat_messages`; se
  cortado, o histórico vive só na sessão do navegador.

## Fora de escopo

- Chat global sem análise selecionada.
- Streaming de resposta (só se sobrar tempo).

## Questões abertas

- Nenhuma.
