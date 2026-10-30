---
id: "007"
titulo: Documentação, nota de pesquisa e entrega
status: rascunho
desafio: [entregáveis, pesquisa]
pontos: Pesquisa e justificativa (15) + Deploy e documentação (10) + Organização (5)
prioridade: P0 (P1 só a comparação com MapBiomas)
---

# 007 — Documentação e entrega: requisitos

## Objetivo

Fechar os entregáveis: README completo, nota de pesquisa de até duas páginas,
relato do uso de IA, vídeo de até três minutos e envio dos links.

## Histórias

- **H7.1** Como avaliador, quero rodar e entender o projeto pelo README, para
  avaliar sem pedir ajuda.
- **H7.2** Como avaliador, quero ler as fontes, alternativas e limitações do
  método, para julgar a qualidade da pesquisa.

## Critérios de aceite (EARS)

### README

- **R7.1** — O README DEVE ter: execução local, arquitetura, método, serviços
  usados, limitações e evidências de testes de processamento e de segurança.
- **R7.2** — O README DEVE documentar cotas dos planos gratuitos (com a data da
  consulta), suspensão por inatividade (Render e Supabase) e retenção dos
  dados.
- **R7.3** — Um workflow agendado DEVE chamar `/health` a cada 3 dias para
  evitar a pausa do Supabase por inatividade.

### Nota de pesquisa (`docs/nota-de-pesquisa.md`, até 2 páginas)

- **R7.4** — A nota DEVE citar pelo menos três fontes primárias conferidas,
  incluindo uma publicação ou metodologia técnica de mapeamento de café.
- **R7.5** — A nota DEVE apresentar duas alternativas consideradas e a
  justificativa da escolha.
- **R7.6** — A nota DEVE informar origem e condições de uso dos dados e
  modelos (Sentinel/Copernicus, Earth Search, LLM, basemap, MapBiomas se usado).
- **R7.7** — A nota DEVE descrever como o resultado foi verificado (sanidade de
  área e inspeção visual de 10 a 20 pontos, sem converter em percentual), um
  erro encontrado com antes e depois, e as limitações do método.
- **R7.8** *(P1)* — ONDE houver comparação com o MapBiomas, ela DEVE ser
  apresentada como concordância com outro produto, não como acurácia.

### Uso de IA e entrega

- **R7.9** — `docs/uso-de-ia.md` DEVE informar ferramentas usadas, como cada
  entrega foi validada e pelo menos um caso concreto em que a IA errou e o
  erro foi pego.
- **R7.10** — O repositório público NÃO DEVE conter segredos nem dados
  pessoais e DEVE ter licença do código e a atribuição dos dados.
- **R7.11** — O vídeo DEVE ter até 3 minutos, mostrar o fluxo completo e a
  imagem adicional, e ter link acessível sem login.
- **R7.12** — Antes do envio, o fluxo completo DEVE ser testado em aba
  anônima com outra conta Google, com o kit e com a imagem adicional.

## Fora de escopo

- Site de documentação separado.

## Questões abertas

- Licença do código (padrão: MIT).
