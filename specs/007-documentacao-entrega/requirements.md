---
id: "007"
titulo: Documentação, nota de pesquisa e entrega
status: em-implementacao
desafio: [entregáveis, pesquisa]
pontos: Pesquisa e justificativa (15) + Deploy e documentação (10) + Organização (5)
prioridade: P0
---

# 007 — Documentação e entrega: requisitos

## Objetivo

Fechar os entregáveis: README completo, nota de pesquisa de até duas páginas,
relato do uso de IA, vídeo de até três minutos e envio dos links.

Boa parte do conteúdo já existe. A calibração, a comparação com o MapBiomas
(T2.5), a imagem adicional (spec 003) e as evidências de produção e de
segredos (specs 002 e 006) foram feitas antes. Esta spec junta tudo, corta a
nota para duas páginas e fecha o que falta: inspeção visual, README, licença e
publicação.

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
  consulta), suspensão por inatividade (Render e Supabase), limites de uso por
  usuário e retenção dos dados.
- **R7.3** — O banco DEVE receber ao menos uma consulta a cada 7 dias, para o
  Supabase não pausar o projeto. O job diário de retenção (R6.15) cumpre esse
  papel; o README DEVE dizer isso e que o GitHub desliga workflows agendados
  após 60 dias sem atividade no repositório.

### Nota de pesquisa (`docs/nota-de-pesquisa.md`)

- **R7.4** — A nota DEVE citar pelo menos três fontes primárias conferidas,
  incluindo uma publicação ou metodologia técnica de mapeamento de café.
- **R7.5** — A nota DEVE apresentar duas alternativas consideradas e a
  justificativa da escolha.
- **R7.6** — A nota DEVE informar origem e condições de uso dos dados e
  modelos: Sentinel/Copernicus, Earth Search, MapBiomas, LLM e basemap.
- **R7.7** — A nota DEVE descrever como o resultado foi verificado (sanidade de
  área e inspeção visual de 10 a 20 pontos, sem converter em percentual), um
  erro encontrado com antes e depois, e as limitações do método.
- **R7.8** — A comparação com o MapBiomas (feita na T2.5 e na T3.3) DEVE ser
  apresentada como concordância com outro produto, não como acurácia.
- **R7.13** — A nota DEVE caber em duas páginas A4 exportada para PDF. O
  detalhamento da calibração e das comparações PODE ficar em `docs/metodo.md`,
  citado pela nota.

### Uso de IA e entrega

- **R7.9** — `docs/uso-de-ia.md` DEVE informar ferramentas usadas, como cada
  entrega foi validada e pelo menos um caso concreto em que a IA errou e o
  erro foi pego.
- **R7.10** — O repositório público NÃO DEVE conter segredos nem dados
  pessoais e DEVE ter licença do código (MIT) e a atribuição dos dados.
- **R7.11** — O vídeo DEVE ter até 3 minutos, mostrar o fluxo completo e a
  imagem adicional, e ter link acessível sem login.
- **R7.12** — Antes do envio, o fluxo completo DEVE ser testado em aba
  anônima com outra conta Google, com o kit e com a imagem adicional.

## Fora de escopo

- Site de documentação separado.
- Workflow de keepalive próprio: o job de retenção já consulta o banco todo dia.
- Novo script de comparação com o MapBiomas: a comparação já está em
  `scripts/calibrate_thresholds.py` e `scripts/compare_dates.py`.

## Questões abertas

- Nenhuma. Licença do código: MIT.
