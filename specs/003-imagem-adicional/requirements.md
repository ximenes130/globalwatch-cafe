---
id: "003"
titulo: Imagem adicional e comparação entre datas
status: aprovado
desafio: [pesquisa]
pontos: Pesquisa e justificativa (15, parcial) + Geoprocessamento (20, parcial)
prioridade: P0 (download, processamento e comparação) / P1 (regra temporal na app)
---

# 003 — Imagem adicional e comparação entre datas: requisitos

## Objetivo

Cumprir a exigência de obter e processar pelo menos uma imagem adicional e usá-la
como argumento técnico. O café é perene e o NDVI dele varia pouco entre a seca e
a chuva. O pasto e as culturas anuais oscilam bastante, e a mata fica alta nas
duas datas. O kit é da seca (16/08/2025); a imagem adicional é da mesma área na
estação chuvosa.

## Histórias

- **H3.1** Como desenvolvedor, quero um script reprodutível que baixe outra
  data da mesma área no mesmo formato do kit, para processá-la pela própria
  aplicação.
- **H3.2** Como avaliador, quero ver a imagem adicional processada no app e o
  que muda entre as datas, para avaliar a robustez do método.

## Critérios de aceite (EARS)

- **R3.1** — O script DEVE buscar no Earth Search (coleção `sentinel-2-c1-l2a`,
  sem autenticação) as cenas do mesmo tile MGRS do kit (`23KLS`) na estação
  chuvosa (dezembro a março) de um intervalo de datas informado. Ele DEVE
  escolher a cena com a menor fração de pixels excluídos pela SCL **dentro do
  recorte do kit**, desempatando por `eo:cloud_cover`, e aceitar `--item` para
  fixar a cena.
- **R3.2** — O script DEVE gerar um GeoTIFF no mesmo formato do kit:
  - bandas B02, B03, B04 e B08 em DN `uint16`, com as mesmas descrições
    (`B02_blue` …);
  - EPSG:32723, com a mesma grade e a mesma extensão do recorte do kit
    (512 × 512, transform idêntico);
  - NoData 0, scale/offset por banda e as tags `ACQUISITION_UTC`,
    `ATTRIBUTION`, `MODIFICATION` e `SOURCE_ITEM`.
- **R3.3** — O script DEVE ler scale/offset dos metadados `raster:bands` do
  item STAC em vez de fixá-los no código.
- **R3.4** — O script DEVE recortar também a SCL correspondente, na resolução
  nativa de 20 m (256 × 256).
- **R3.5** — SE a cena estiver em outro CRS ou a janela do recorte não cair em
  pixels inteiros da grade da cena, ENTÃO o script DEVE parar com erro, sem
  reamostrar.
- **R3.6** — O script DEVE gravar, junto dos arquivos:
  - `ATRIBUICAO.txt` equivalente ao do kit: cena, data de aquisição, URL STAC,
    data de acesso e termos;
  - `metadados.json` e `fonte_stac.json`, como no kit;
  - um `SHA256SUMS.txt`.
- **R3.7** — QUANDO o arquivo adicional for enviado pela aplicação, O SISTEMA
  DEVE processá-lo pelo mesmo fluxo e com os mesmos parâmetros da spec 002,
  sem tratamento especial.
- **R3.8** — Um script de comparação DEVE rodar o mesmo pipeline da aplicação
  nas duas datas e salvar em `docs/evidencias/comparacao-datas/`:
  - a tabela de estatísticas das duas análises;
  - a transição por pixel: candidato nas duas datas, só na seca, só na chuva
    ou em nenhuma;
  - a amplitude de NDVI entre as datas em cada classe de transição;
  - uma figura com as duas imagens, o mapa de transição e os histogramas de
    amplitude.
- **R3.9** — A comparação DEVE trazer as classes do MapBiomas em cada classe de
  transição, apresentadas como concordância com outro produto e nunca como
  acurácia (C1.2).
- **R3.10** *(P1)* — ONDE o usuário enviar uma segunda imagem da mesma área, O
  SISTEMA DEVE manter como candidato apenas o pixel cuja amplitude de NDVI
  entre as datas fique abaixo de `ndvi_amplitude_max`, registrando a regra em
  `params`.

## Fora de escopo

- Série temporal completa (documentada como evolução).
- Download de cenas pela aplicação web.
- Recalibrar os limiares da spec 002 para a data chuvosa: a app usa um único
  conjunto de parâmetros, e a diferença entre as datas é justamente o achado.

## Questões resolvidas

- **Qual cena?** Busca em 30/10/2026, de dez/2024 a abr/2026, no tile 23KLS.
  A escolhida é `S2B_T23KLS_20260110T131730_L2A`, de 10/01/2026: pico da
  chuva, no mesmo ano agrícola do kit. Ela tem 0% de pixels excluídos pela SCL
  no recorte e 0,19% de nuvem na cena inteira, o mesmo processing baseline do
  kit (05.11) e o mesmo scale/offset (0,0001 e −0,1). A janela cai em pixels
  inteiros da grade da cena.
  - Alternativas conferidas: 01/12/2025 (0% excluído) e 16/03/2026 (0,47%
    excluído). 17/02/2026 foi descartada: 12,9% de nuvem e sombra no recorte.
