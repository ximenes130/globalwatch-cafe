---
id: "002"
titulo: Processamento da imagem e classificação de áreas potenciais
status: rascunho
desafio: [2, 3]
pontos: Geoprocessamento e classificação (20)
prioridade: P0
---

# 002 — Processamento e classificação: requisitos

## Objetivo

Receber um GeoTIFF multiespectral, processá-lo de verdade em Python e devolver
áreas potenciais de café como polígonos, com índices espectrais, áreas em
hectares, parâmetros salvos e uma justificativa técnica da classificação.

## Histórias

- **H2.1** Como usuário, quero enviar uma imagem Sentinel-2 e receber as áreas
  potenciais de café, para ter um ponto de partida de mapeamento.
- **H2.2** Como analista, quero saber quais regras e parâmetros geraram cada
  resultado, para auditar e reproduzir a análise.
- **H2.3** Como avaliador, quero que um arquivo diferente do kit gere um
  resultado diferente, para confirmar que nada é pré-calculado.

## Critérios de aceite (EARS)

### Leitura

- **R2.1** — QUANDO receber um GeoTIFF que passou na validação (R6.5–R6.7), O
  SISTEMA DEVE processar o próprio arquivo enviado e registrar a análise com
  status `concluida` ou `erro`.
- **R2.2** — O SISTEMA DEVE converter DN em reflectância **uma única vez**,
  `reflectância = DN * scale + offset`, com scale/offset lidos do arquivo e,
  na ausência deles, os valores do kit (0,0001 e -0,1), registrando em
  `params` qual origem foi usada.
- **R2.3** — O SISTEMA DEVE tratar DN = 0 como NoData e excluí-lo de índices,
  classificação e áreas.
- **R2.4** — O SISTEMA DEVE assumir a ordem de bandas B02, B03, B04, B08
  (azul, verde, vermelho, NIR), usando as descrições das bandas quando
  existirem.
- **R2.5** — O SISTEMA DEVE ler a data de aquisição da tag `ACQUISITION_UTC`;
  SE ela não existir, ENTÃO DEVE registrar a data como não informada.

### Máscara de qualidade

- **R2.6** — ONDE a SCL for enviada, O SISTEMA DEVE reamostrá-la para a grade
  de 10 m por vizinho mais próximo e excluir as classes 0 (sem dado), 1
  (saturado), 3 (sombra de nuvem), 6 (água), 8, 9, 10 (nuvem e cirrus) e 11
  (neve).
- **R2.7** — SE a SCL não for enviada, ENTÃO O SISTEMA DEVE mascarar água por
  NDWI (verde e NIR) acima do limiar em `params`.

### Índices e regra

- **R2.8** — O SISTEMA DEVE calcular NDVI para todos os pixels válidos.
- **R2.9** — O SISTEMA DEVE calcular um segundo índice (GNDVI) para apoiar a
  separação entre mata e café. *(P1: se cortado, fica só NDVI.)*
- **R2.10** — O SISTEMA DEVE marcar como candidato o pixel válido com NDVI
  dentro de `[ndvi_min, ndvi_max]` (ponto de partida 0,55–0,78), excluindo o
  topo da distribuição associado a mata e eucalipto.
- **R2.11** — O SISTEMA DEVE aplicar abertura e fechamento morfológico e
  remover manchas menores que `area_min_ha` (padrão 0,5 ha).

### Vetorização e áreas

- **R2.12** — O SISTEMA DEVE vetorizar a máscara final, simplificar com
  tolerância de meio pixel e calcular `area_ha` no CRS projetado (UTM) antes
  de reprojetar para WGS84.
- **R2.13** — O GeoJSON DEVE seguir a RFC 7946 (WGS84, lon/lat) e cada feição
  DEVE ter `id`, `area_ha`, `ndvi_medio`, `classe: "area_potencial_cafe"` e
  `validado: false`.
- **R2.14** — O SISTEMA DEVE calcular e salvar: área total do recorte, área
  válida, área mascarada, área potencial, número de polígonos e estatísticas
  do NDVI (mín., p5, mediana, p95, máx.).
- **R2.15** — QUANDO processar o arquivo do kit, O SISTEMA DEVE reportar área
  total de 2.621,44 ha.

### Saídas e rastreabilidade

- **R2.16** — O SISTEMA DEVE gerar e guardar no storage privado: PNG RGB
  realçado, PNG da classificação (transparente fora dos candidatos), PNG com
  os polígonos desenhados para download, GeoJSON e os bounds em WGS84.
- **R2.17** — O SISTEMA DEVE salvar `params` e `method_version` com cada
  análise; o mesmo arquivo com os mesmos parâmetros DEVE gerar o mesmo
  resultado.
- **R2.18** — O SISTEMA DEVE gerar uma justificativa técnica estruturada
  (regras aplicadas, limiares, máscaras, limitações) a partir de `params` e
  das estatísticas, usada pela UI e pelo chat.
- **R2.19** — SE o processamento falhar, ENTÃO O SISTEMA DEVE salvar a análise
  com status `erro` e uma mensagem compreensível, sem stack trace.
- **R2.20** — QUANDO a máscara final estiver vazia, O SISTEMA DEVE concluir a
  análise com zero polígonos (não é erro).

### API

- **R2.21** — O SISTEMA DEVE expor `POST /analyses`, `GET /analyses`,
  `GET /analyses/{id}` e `DELETE /analyses/{id}`, todos protegidos e isolados
  por usuário (R6.1–R6.3).

## Fora de escopo

- Classificador supervisionado ou modelo treinado (alternativa documentada na
  nota de pesquisa).
- Processamento assíncrono em fila (documentado como evolução).
- Imagens com mais de 2048 x 2048 px.

## Questões abertas

- Limiar final de NDVI e uso do GNDVI: calibrar olhando histograma e imagem
  do kit na T2.5.
