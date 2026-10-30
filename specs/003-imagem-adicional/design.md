---
id: "003"
titulo: Imagem adicional e comparação entre datas
status: em-implementacao
---

# 003 — Imagem adicional e comparação entre datas: design

## Visão geral

```text
download_additional_scene.py
  POST /v1/search (grid:code = MGRS-23KLS, datas) ─> itens candidatos
  para cada item: lê a SCL só na janela do kit ─> fração com problema de aquisição
  escolhe a menor fração (desempate: eo:cloud_cover) ou usa --item
  lê B02/B03/B04/B08 por janela (COG, sem reamostrar) ─> empilha uint16 + tags
  lê a SCL por janela (20 m)
  └─> data/adicional/<item_id>/
        imagem_multiespectral.tif  qualidade_scl.tif
        ATRIBUICAO.txt  metadados.json  fonte_stac.json  SHA256SUMS.txt

compare_dates.py (kit + adicional, mesmo pipeline da app)
  └─> docs/evidencias/comparacao-datas/
        resumo.txt  comparacao.jpg
```

A grade de referência vem do próprio `data/exemplo/imagem_multiespectral.tif`
(CRS, transform, largura e altura). O kit e a cena nova estão no mesmo tile
MGRS (23KLS), então a janela cai em pixels inteiros dos COGs e a leitura não
reamostra nada. O script confere isso e para se não for o caso (R3.5).

## Componentes e arquivos

| Arquivo | Responsabilidade |
| --- | --- |
| `scripts/download_additional_scene.py` | Busca, escolha da cena, recorte, empilhamento, tags, atribuição, SHA256 |
| `scripts/compare_dates.py` | Roda o pipeline nas duas datas e gera tabela, transição, amplitude, MapBiomas e figura |
| `scripts/calibrate_thresholds.py` | Já tem a leitura do MapBiomas e o realce de RGB; a comparação importa essas funções em vez de copiá-las |
| `scripts/smoke_analysis.sh` | Passa a aceitar `IMAGE` e `SCL` para enviar a cena adicional (T3.4) |
| `data/adicional/<item_id>/` | Saída versionada (cerca de 1,5 MB, como o kit) |
| `docs/evidencias/comparacao-datas/` | Evidência da comparação |
| `docs/nota-de-pesquisa.md` | Parágrafo da imagem adicional (dados, verificação, limitações) |
| `backend/app/processing/temporal.py` | *(P1)* regra de amplitude |

## Contratos

### Download

```sh
backend/.venv/bin/python scripts/download_additional_scene.py \
  --start 2025-12-01 --end 2026-03-31 [--item S2B_T23KLS_20260110T131730_L2A]
```

- Busca: `POST https://earth-search.aws.element84.com/v1/search` com
  `collections`, `datetime` e `query: {"grid:code": {"eq": "MGRS-23KLS"}}`,
  paginando pelo link `next`.
- Filtro de estação: só meses de dezembro a março (R3.1), mesmo que o
  intervalo informado seja maior.
- Fração com problema de aquisição: pixels da SCL na janela do kit cujas
  classes estão em `SCL_EXCLUDE` (o mesmo tuple de
  `backend/app/processing/params.py`) **menos a água (6)**, divididos pelo
  total da janela. A app exclui a água da análise, mas ela é cobertura do solo
  e aparece nas duas datas; contá-la faria um açude decidir entre duas cenas
  limpas. Isso aconteceu na primeira execução: 6 pixels de água (0,01%) deram a
  vitória a 01/12/2025 sobre 10/01/2026, as duas sem nuvem no recorte. Cena com
  sem-dado (classe 0) no recorte conta como problema; assim, cenas da órbita
  que cobre só metade do tile ficam para trás sozinhas.
- Saída, com os mesmos nomes de arquivo do kit (para o upload ser idêntico):

| Arquivo | Conteúdo |
| --- | --- |
| `imagem_multiespectral.tif` | 4 bandas `uint16`, 512 × 512, EPSG:32723, transform do kit, NoData 0, deflate em blocos 256 × 256. Descrições `B02_blue`, `B03_green`, `B04_red`, `B08_nir`. Scale/offset por banda vindos de `raster:bands`. Tags: `ACQUISITION_UTC` (`properties.datetime`), `ATTRIBUTION` ("Contains modified Copernicus Sentinel data (<ano>)"), `MODIFICATION` e `SOURCE_ITEM` |
| `qualidade_scl.tif` | 1 banda `uint8`, 256 × 256, 20 m, NoData 0, descrição `Sentinel-2_SCL_20m` |
| `ATRIBUICAO.txt` | Mesmo texto do kit com a cena, a aquisição, a URL STAC, a data de acesso e os termos da coleção |
| `metadados.json` | Mesma estrutura do kit (`item`, `fonte_stac`, `aquisicao_utc`, `crs`, `shape`, `bandas` com scale/offset/URL, `scl`, `alteracoes`). As chaves seguem o arquivo do kit, que é o formato de referência, e não os identificadores do nosso código |
| `fonte_stac.json` | O item STAC como veio do catálogo |
| `SHA256SUMS.txt` | Hash dos cinco arquivos acima, no formato do `sha256sum` |

Depois de gravar, o script reabre o TIFF com o `read_image` do backend e
confere a ordem das bandas, a radiometria vinda das tags e a área total de
2.621,44 ha. Se o leitor da app não aceitar o arquivo, o download falha ali,
e não no upload.

### Comparação

```sh
backend/.venv/bin/python scripts/compare_dates.py [--additional data/adicional/<item_id>]
```

- Cada data passa pelo `run_pipeline` (mesmos `Params`, R3.7) para as
  estatísticas, e pelas funções de baixo nível (`read_image`, `quality_mask`,
  `ndvi`, `classify`) para os arrays por pixel. São as mesmas funções, então os
  números batem com os da app (C2.3); a T3.4 confere isso contra a análise em
  produção.
- **Base comum:** pixels utilizáveis nas duas datas (sem NoData e fora da
  máscara de qualidade em ambas).
- **Transição** (sobre a base comum, com o resultado após morfologia e área
  mínima): candidato nas duas, só na seca (kit), só na chuva, nenhuma.
- **Amplitude:** `|NDVI_chuva − NDVI_seca|` por pixel. Mediana e quartis por
  classe de transição, e histograma.
- **MapBiomas** (R3.9): hectares de café, pasto, mata e mosaico em cada classe
  de transição, com a mesma leitura e a mesma ressalva da calibração (30 m,
  2024, modelo e não gabarito).
- `resumo.txt`: as duas tabelas de estatísticas lado a lado (área total,
  área potencial, polígonos, área excluída por nível, NDVI médio), a matriz de
  transição em hectares, a amplitude por classe, o MapBiomas e as fontes.
- `comparacao.jpg`: RGB da seca, RGB da chuva, mapa de transição e
  histogramas de amplitude.

### Regra temporal *(P1)*

- `POST /analyses` aceita `image_2` e `scl_2` opcionais. Os dois arquivos
  precisam ter o mesmo CRS e a mesma grade; caso contrário, 422.
- `temporal.py`: `amplitude_mask(ndvi_a, ndvi_b, usable, max_amplitude)`
  entra na cascata como nível `N3c high_amplitude`, antes da morfologia.
- `ndvi_amplitude_max` é escolhido pelo histograma de amplitude dos
  candidatos da seca, gerado em T3.3, e não para concordar com o MapBiomas,
  pelo mesmo motivo da calibração.

## Decisões

| Decisão | Alternativa recusada | Motivo |
| --- | --- | --- |
| Earth Search (mesma fonte do kit) | Copernicus Data Space; Google Earth Engine | Sem autenticação e mesmo processamento L2A do kit; GEE exige conta e tem restrição de uso |
| Busca STAC com `urllib` | `pystac-client` | Uma chamada `POST /search` com paginação não justifica uma dependência nova (regra de cadeia de suprimentos); o backend já fala REST com `urllib` no Storage |
| Filtrar por `grid:code` (tile MGRS) | Filtrar por bbox da área | O bbox também traz cenas de tiles vizinhos, em outra grade; o tile garante a mesma grade e leitura sem reamostragem |
| Escolher pela SCL dentro do recorte | Só `eo:cloud_cover` da cena | A nuvem da cena inteira não diz nada sobre os 26 km² do recorte; 17/02/2026 tem 3,7% de nuvem na cena e 12,9% no recorte |
| Água fora do critério de escolha | Usar `SCL_EXCLUDE` inteiro | Água é cobertura do solo, não qualidade da aquisição; continua excluída na análise pela app |
| Mesmo tile e grade do kit | Reprojetar para outra grade | Comparação pixel a pixel sem reamostragem |
| Scale/offset do STAC | Valores fixos | O offset depende do processing baseline (R3.3) |
| Comparação roda o pipeline localmente | Ler os GeoJSON das análises da app | A transição por pixel precisa dos arrays, que a app não guarda; o pipeline é determinístico, e a T3.4 confere que os números batem com a app |
| Mesmos parâmetros nas duas datas | Limiares próprios para a chuva | A app tem um único método; com pasto verde na chuva, o candidato da data chuvosa cresce, e isso mostra por que a seca foi escolhida (design da 002) |

## Riscos

- **Pasto verde na chuva:** o candidato da data chuvosa fica bem maior que o
  da seca. É esperado, e é o achado: vai para a nota como argumento da data
  seca e da regra de amplitude. Não é motivo para recalibrar.
- **Diferença de iluminação entre as datas:** em janeiro o sol está mais alto
  que em agosto. A L2A já é reflectância de superfície, mas sem correção BRDF,
  então a amplitude mede também um pouco de geometria de iluminação.
  Declarado como limitação.
- **Earth Search fora do ar:** os arquivos ficam versionados em
  `data/adicional/`, e o hash permite conferi-los sem baixar de novo.
- **Cobertura do tile:** cenas da órbita que cobre só metade do tile podem
  ter sem-dado no recorte. Elas contam como excluídas e perdem a escolha.

## Estratégia de testes

| Requisito | Teste |
| --- | --- |
| R3.1 | Saída do script lista as candidatas com a fração com problema de aquisição no recorte; a escolhida é a de menor fração |
| R3.2, R3.3, R3.4 | Autoverificação do script: shape (4, 512, 512) e (1, 256, 256), CRS e transform iguais aos do kit, tags e descrições presentes, `read_image` aceita o arquivo e a área total é 2.621,44 ha |
| R3.5 | Rodar com um `--item` de outro tile e confirmar que o script para sem gravar nada |
| R3.6 | `sha256sum -c SHA256SUMS.txt` na pasta de saída |
| R3.7 | Upload pela app em produção; análise `completed` com os mesmos números do `resumo.txt` |
| R3.8, R3.9 | `resumo.txt` e `comparacao.jpg` gerados; soma das classes de transição igual à base comum |
| R3.10 | `test_temporal.py` com dois rasters sintéticos |
