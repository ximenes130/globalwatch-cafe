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
| `backend/app/processing/temporal.py` | *(P1)* leitura da segunda imagem, checagem de grade e máscara de amplitude |
| `backend/app/processing/{params,classification,pipeline,rationale}.py`, `backend/app/{worker,routes/analyses}.py` | *(P1)* parâmetro, nível N3c, segunda imagem no pipeline, passo na justificativa, arquivos extras no Storage, campos do upload |

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
- **MapBiomas** (R3.9): hectares de cada classe do MapBiomas em cada classe
  de transição e a amplitude mediana de cada uma, com a mesma leitura e a
  mesma ressalva da calibração (30 m, 2024, modelo e não gabarito).
- **Matriz de níveis:** hectares por nível da cascata, seca × chuva, para
  mostrar para onde vai a área potencial de uma data na outra.
- `resumo.txt`: as duas tabelas de estatísticas lado a lado (área total,
  área potencial, polígonos, área excluída por nível, NDVI médio), a matriz de
  transição em hectares, a amplitude por classe, o MapBiomas e as fontes.
- `comparacao.jpg`: RGB da seca, RGB da chuva, mapa de transição e
  histogramas de amplitude.

### Regra temporal *(P1)*

Proposta revisada depois da T3.3: a versão aprovada era curta demais para
implementar e escolhia o limiar por um histograma que não tem vale.

- **API:** `POST /analyses` aceita `image_2` e `scl_2` opcionais. A imagem
  principal (`image`) é a classificada. A segunda serve só para medir a
  amplitude, e a ordem das datas não importa porque a amplitude é absoluta.
- **Grade diferente:** a checagem é feita no pipeline. Se as duas imagens não
  tiverem o mesmo CRS, o mesmo transform e o mesmo tamanho, a análise termina
  `failed` com "A segunda imagem precisa ter a mesma grade da primeira (mesmo
  recorte, CRS e resolução)."
  - Muda o "422" da versão anterior: hoje toda leitura de raster acontece no
    worker, e o 422 síncrono fica para a validação de upload da spec 006, que
    vai abrir os cabeçalhos no request.
- **Qualidade:** a máscara de qualidade (N1) passa a juntar as duas datas.
  Pixel com nuvem, sombra, água ou sem dado em qualquer uma delas sai em N1.
  Assim, nenhum pixel é aprovado sem ter sido medido nas duas datas.
- **Cascata:** um nível novo, `N3c high_amplitude`, logo depois de N3/N3b e
  antes da morfologia. O pixel que passou na faixa de NDVI da imagem principal
  sai se `|NDVI_2 − NDVI_1| ≥ ndvi_amplitude_max`. Sem segunda imagem, o nível
  existe com 0 ha.
  - O código `uint8` do nível é 7 e é acrescentado ao fim de `CODES`, para não
    mudar os códigos existentes.
  - Em `EXCLUSION_LEVELS`, a ordem segue a cascata.
- **Parâmetro:** `ndvi_amplitude_max = 0.25`, vindo da literatura e não do
  dado. Em Souza et al. (2019), o componente sazonal do NDVI vai de −0,05 a
  0,06 no café (0,11 de pico a pico) e de −0,15 a 0,10 no pasto (0,25).
  - Regra: sai o que oscila pelo menos tanto quanto o pasto típico oscila no
    ano.
  - Por que não pelo histograma: os candidatos da seca têm amplitude unimodal
    (pico em 0,18–0,20), sem vale para separar classes.
  - Por que não pelo MapBiomas: escolher por ele tornaria a comparação
    circular.
  - Limitação declarada: uma diferença entre duas datas Sentinel-2 não é o
    mesmo que o componente sazonal de uma série. Ela também carrega diferença
    de iluminação e de fenologia do ano.
- **Rastreabilidade (C2.3):**
  - `method_version` passa a `spectral-rules-1.1`, porque a cascata ganhou um
    nível.
  - `params` registra `ndvi_amplitude_max` e, com a segunda imagem, um bloco
    `second_image` com data de aquisição, radiometria e ordem das bandas.
  - `stats.excluded_area_ha` ganha `high_amplitude`.
  - `stats` ganha `second_acquired_at` (`null` sem segunda imagem).
  - Nenhuma migration: tudo cabe nos `jsonb` existentes.
- **Justificativa:** o passo N3c entra no `rationale` só quando há segunda
  imagem, com a regra, o limiar, os hectares, o porquê e a referência
  `souza2019`. A limitação "uma única data" é trocada por "duas datas, sem
  série temporal".
- **Storage:** com a segunda imagem, o worker também grava `original_2.tif` e
  `scl_2.tif`. O `DELETE` apaga os dois.
- **Fora desta task:** o campo de segunda imagem na UI (spec 004) e a menção
  no chat (spec 005). Elas leem `stats` e `rationale`, que já trazem tudo.

Efeito no kit com a cena de 10/01/2026, calculado com a mesma morfologia e a
mesma área mínima (simulação da T3.3, antes de implementar):

| `ndvi_amplitude_max` | Área potencial | Café do MapBiomas marcado | Área marcada em café do MapBiomas |
| --- | --- | --- | --- |
| sem regra | 214,5 ha | 42% | 10% |
| 0,30 | 168,6 ha | 41% | 12% |
| **0,25** | **103,0 ha** | **35%** | **17%** |
| 0,20 | 47,5 ha | 24% | 24% |
| 0,15 | 17,9 ha | 6% | 15% |

As colunas do MapBiomas são conferência depois da escolha, não o critério. Com
0,25, a cana quase some (de 10,1 para 0,2 ha), a lavoura temporária cai de
41,9 para 13,6 ha e a mata de 43,4 para 18,4 ha. O café do MapBiomas cai menos:
de 20,7 para 17,1 ha.

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

- **Limiares da seca na chuva:** a expectativa era que o pasto verde
  inflasse a área potencial da data chuvosa. A T3.3 mostrou outra coisa: ela
  cai para 139 ha, porque o NDVI de quase toda a vegetação passa do teto de
  0,72. O pasto entra (83 ha), mas a área da seca sai (191 ha), e só 10 ha
  coincidem. É o achado: vai para a nota como argumento da data seca. Não é
  motivo para recalibrar.
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
| R3.10 | `test_temporal.py` (amplitude, grade diferente, máscara das duas datas) com rasters sintéticos; testes de classificação, pipeline, justificativa, worker e API estendidos; kit + cena de janeiro dá 103,0 ha |
