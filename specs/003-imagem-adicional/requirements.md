---
id: "003"
titulo: Imagem adicional e comparação entre datas
status: rascunho
desafio: [pesquisa]
pontos: Pesquisa e justificativa (15, parcial) + Geoprocessamento (20, parcial)
prioridade: P0 (download e processamento) / P1 (regra temporal na app)
---

# 003 — Imagem adicional e comparação entre datas: requisitos

## Objetivo

Cumprir a exigência de obter e processar pelo menos uma imagem adicional e usá-la
como argumento técnico: café é perene e mantém NDVI estável entre seca e chuva;
pasto e cultura anual oscilam; mata fica alta nas duas datas.

## Histórias

- **H3.1** Como desenvolvedor, quero um script reprodutível que baixe outra
  data da mesma área no mesmo formato do kit, para processá-la pela própria
  aplicação.
- **H3.2** Como avaliador, quero ver a imagem adicional processada no app e o
  que muda entre as datas, para avaliar a robustez do método.

## Critérios de aceite (EARS)

- **R3.1** — O script DEVE buscar no Earth Search (coleção `sentinel-2-c1-l2a`,
  sem autenticação) uma cena da estação chuvosa (jan a mar de 2025 ou 2026)
  que cubra a `area_estudo.geojson`, priorizando menor cobertura de nuvem.
- **R3.2** — O script DEVE gerar um GeoTIFF no mesmo formato do kit: bandas
  B02, B03, B04, B08 em DN `uint16`, EPSG:32723, mesma grade e extensão do
  recorte do kit, NoData 0, tags de scale/offset e `ACQUISITION_UTC`.
- **R3.3** — O script DEVE ler scale/offset dos metadados `raster:bands` do
  item STAC em vez de fixá-los no código.
- **R3.4** — O script DEVE recortar também a SCL correspondente na resolução
  nativa de 20 m.
- **R3.5** — O script DEVE gravar, junto dos arquivos, atribuição equivalente
  ao `ATRIBUICAO.txt` do kit (cena, data de aquisição, URL STAC, data de
  acesso, termos) e um `SHA256SUMS.txt`.
- **R3.6** — QUANDO o arquivo adicional for enviado pela aplicação, O SISTEMA
  DEVE processá-lo pelo mesmo fluxo da spec 002, sem tratamento especial.
- **R3.7** — Um script de comparação DEVE produzir, para as duas análises, a
  tabela de estatísticas e a variação de NDVI por classe (candidato nas duas,
  só na seca, só na chuva), salva em `docs/evidencias/`.
- **R3.8** *(P1)* — ONDE o usuário enviar uma segunda imagem da mesma área, O
  SISTEMA DEVE manter como candidato apenas o pixel cuja amplitude de NDVI
  entre as datas fique abaixo de `ndvi_amplitude_max`, registrando a regra em
  `params`.

## Fora de escopo

- Série temporal completa (documentada como evolução).
- Download de cenas pela aplicação web.

## Questões abertas

- Qual cena escolher se jan–mar tiver nuvem sobre a área? Alternativa: abril
  ou dezembro, documentando o motivo.
