---
id: "002"
titulo: Processamento da imagem e classificação de áreas potenciais
status: rascunho
---

# 002 — Processamento e classificação: design

## Visão geral

Processamento **síncrono** dentro do request: um recorte 512 x 512 leva poucos
segundos. Em produção iria para fila com status de job (README explica).

```text
upload ─> validação (006) ─> leitura ─> máscara ─> índices ─> regra hierárquica
       ─> morfologia ─> vetorização ─> render ─> storage + linha em analyses
```

A regra é uma **cascata de exclusões com limiares explícitos**, inspirada na
classificação hierárquica de Parreiras et al. (2025), que separa primeiro
vegetação antrópica, depois culturas perenes de pasto e cultura anual, e por
fim café de silvicultura. Lá cada nível é um Random Forest com série temporal
e SWIR; aqui cada nível é um limiar auditável sobre uma única data e quatro
bandas. Essa troca é a principal limitação do método e aparece na
justificativa (C1.4).

```text
pixel do recorte
 ├─ N0  NoData (DN = 0)                                   → excluído: no_data
 ├─ N1  máscara de qualidade (SCL ou NDWI)                → excluído: quality_mask
 ├─ N2  NDVI < ndvi_min       (solo, pasto seco, anual)   → excluído: low_vegetation
 ├─ N3  NDVI > ndvi_max       (mata, eucalipto)           → excluído: dense_canopy
 ├─ N3b GNDVI < gndvi_min     (opcional, se calibrado)    → excluído: low_chlorophyll
 ├─ N4  abertura/fechamento + mancha < min_area_ha        → excluído: small_patch
 └─ restante                                              → área potencial de café
```

Cada nível registra quantos hectares excluiu. A soma fecha com a área total do
recorte, o que dá um teste simples e deixa o chat explicar *por que* uma área
ficou de fora usando números do processamento (C2.1).

## Base na literatura

O que cada etapa toma de fontes publicadas e o que não dá para reproduzir com
o kit (uma data, bandas B02, B03, B04, B08, sem rótulos).

| Etapa | Referência | O que adotamos | O que não reproduzimos e por quê |
| --- | --- | --- | --- |
| Data seca como data única | Maskell et al. (2021); Parreiras et al. (2025) | Maskell levanta a hipótese de que imagens da seca capturam melhor a diferença de folhagem entre culturas arbóreas; em Parreiras, julho é o 2º mês mais importante para separar perenes de pasto. O kit é de 16/08/2025 (seca): pasto senescente cai no NDVI, café (perene, sempre-verde) se mantém | Composições seca + chuva (ambos usam as duas estações): a app recebe um arquivo por vez; a segunda data entra pela spec 003 |
| N2: piso de NDVI | Rouse et al. (1974) para o índice; Parreiras et al. (2025) para a separação perene x pasto | Corte inferior de NDVI separa o pico de pasto seco/solo do pico de vegetação perene | Parreiras usa o ano inteiro e 4 índices; aqui é um limiar calibrado no histograma |
| N3: teto de NDVI | Parreiras et al. (2025) relatam confusão espectral café x eucalipto; Souza et al. (2019) apontam que trabalhos anteriores confundem café com pasto e com vegetação nativa | Dossel fechado (mata ciliar, eucalipto) satura o NDVI acima do café em produção, que deixa solo visível entre linhas | O nível 3 de Parreiras depende de SWIR e do ano inteiro; o kit não tem SWIR. Café adensado ou sombreado vai ser cortado junto com mata (limitação) |
| GNDVI como 2º índice | Gitelson, Kaufman e Merzlyak (1996); Parreiras et al. (2025); Maskell et al. (2021) | GNDVI usa a banda verde, mais sensível à clorofila que o vermelho (Gitelson). Em Parreiras, GNDVI foi o índice mais importante na separação de perenes e, com a banda verde, somou 39% da importância. Maskell manteve o GCVI (também verde/NIR) entre as variáveis da seca | No kit, NDVI e GNDVI têm correlação de 0,96 nos pixels SCL 4 (exploração de 30/10): numa data só, o GNDVI tende a repetir o NDVI. Por isso é calculado e reportado sempre, mas só vira condição (`gndvi_min`) se a T2.5 mostrar que remove falsos positivos visíveis |
| NDWI como máscara sem SCL | McFeeters (1996) | NDWI = (verde − NIR)/(verde + NIR); água fica positiva | MNDWI (Xu, 2006) precisa de SWIR, ausente no kit |
| SCL como máscara | Documentação da SCL do Sentinel-2 L2A (classes 0–11) | Exclusão de sem dado, saturado, sombra de nuvem, água, nuvem, cirrus e neve; reamostragem por vizinho mais próximo | A SCL não é mapa de uso do solo; não é usada como classe de vegetação |
| Textura (GLCM) | Parreiras et al. (2025) | Não adotada: lá a textura teve importância média menor que bandas e índices, e centenas de variáveis com importância ≤ 0 | Custo e explicação não se pagam num recorte de 10 m |
| Amplitude entre datas | Souza et al. (2019) | Amplitude sazonal do NDVI do café é a mais estreita entre café, pasto e vegetação nativa (componente sazonal de −0,05 a 0,06 contra −0,15 a 0,10 no pasto). Base de R3.8 (spec 003) | A amplitude separa café de pasto, não de mata (a de mata também é estreita); o teto de NDVI continua necessário |
| Estágios de manejo | Parreiras et al. (2025); Maskell et al. (2021) | Limitação declarada: café recém-plantado, esqueletado ou recepado expõe solo e fica abaixo de `ndvi_min`. Maskell obteve acurácia de usuário de 71% para café jovem e 56% para consorciado mesmo com RF e radar | Separar estágios exige série temporal densa |

Referências conferidas em [Referências](#referências). A nota de pesquisa
(spec 007) usa esta tabela como ponto de partida.

## Componentes e arquivos

| Arquivo | Responsabilidade |
| --- | --- |
| `backend/app/processing/reader.py` | Abre o raster (MemoryFile), aplica scale/offset uma vez, máscara de NoData, lê data e CRS |
| `backend/app/processing/masking.py` | SCL (vizinho mais próximo, classes excluídas) ou NDWI |
| `backend/app/processing/indices.py` | NDVI, GNDVI, NDWI com divisão segura |
| `backend/app/processing/classification.py` | Cascata N2–N4: limiares, morfologia (`scipy.ndimage`), remoção de manchas pequenas e contagem por nível de exclusão |
| `backend/app/processing/vectorization.py` | `rasterio.features.shapes`, simplificação, área em UTM, reprojeção para WGS84 |
| `backend/app/processing/render.py` | PNG RGB (realce p2–p98), PNG da classificação, PNG com polígonos |
| `backend/app/processing/rationale.py` | Monta a justificativa estruturada, incluindo referências e limitações |
| `backend/app/processing/params.py` | `Params` (dataclass/pydantic) + `METHOD_VERSION` + `METHOD_REFERENCES` |
| `backend/app/processing/pipeline.py` | Orquestra e devolve `AnalysisResult` |
| `backend/app/routes/analyses.py` | Endpoints |
| `backend/app/storage.py` | Upload/download no Supabase Storage, URLs assinadas |

## Parâmetros versionados

```json
{
  "method_version": "spectral-rules-1.0",
  "radiometry": {"scale": 0.0001, "offset": -0.1, "source": "file_tags"},
  "scl_exclude": [0, 1, 3, 6, 8, 9, 10, 11],
  "ndwi_water_min": 0.0,
  "ndvi_min": 0.55,
  "ndvi_max": 0.78,
  "gndvi_min": null,
  "morphology_iterations": 1,
  "min_area_ha": 0.5,
  "simplify_tolerance_px": 0.5
}
```

Valores de partida; os finais saem da calibração (T2.5) e são registrados
aqui. `ndwi_water_min = 0,0` segue a leitura de McFeeters (água positiva).

### Exploração preliminar do kit (30/10, script descartável)

Feita para checar se os valores de partida fazem sentido; **não substitui a
T2.5**, que refaz com script versionado e salva as evidências.

- Histograma de NDVI bimodal: um pico em 0,28–0,34 (pasto seco e solo, coerente
  com agosto) e outro em 0,76–0,82 (dossel denso). `ndvi_max = 0,78` corta no
  meio do pico alto; a T2.5 decide olhando a imagem.
- NDVI nos pixels SCL 4 (vegetação): p5 0,43, mediana 0,73, p95 0,83.
- Correlação NDVI x GNDVI nos pixels SCL 4: 0,96.
- Faixa 0,55–0,78 sem morfologia: 801 ha (30,6% do recorte); NDVI > 0,78: 532 ha.
- SCL do kit só tem as classes 2, 4, 5 e 7: nenhuma é excluída por
  `scl_exclude`, então a máscara de qualidade não remove nada neste recorte.

### Calibração (T2.5)

1. Histograma de NDVI e GNDVI dos pixels válidos, com os limiares marcados.
2. Inspeção visual da máscara sobre o RGB: talhões em linhas regulares devem
   cair dentro; mata ciliar (faixas ao longo de drenagens) e eucalipto (blocos
   homogêneos muito escuros no visível) devem cair em `dense_canopy`.
3. GNDVI só entra se houver pixels visivelmente errados que o NDVI não separa
   e o GNDVI sim; caso contrário, `gndvi_min` fica `null` com o motivo
   registrado.
4. Antes/depois do ajuste salvo em `docs/evidencias/` (é o "erro encontrado"
   mais provável da nota). Sem percentual de acerto: o kit não tem gabarito.

## Contratos

- `POST /analyses` — `multipart/form-data`: `image` (obrigatório), `scl`
  (opcional). → `201 {"id", "status"}`; erros 400/413/415/422/429 (006).
- `GET /analyses` → lista do usuário: `id`, `filename`, `created_at`,
  `status`, `acquired_at`, `stats.potential_area_ha`.
- `GET /analyses/{id}` → `id`, `status`, `filename`, `acquired_at`, `crs`,
  `bounds_wgs84` (`[[lon,lat] x 4]`), `stats`, `params`, `method_version`,
  `rationale`, `urls` assinadas (`rgb_png`, `classification_png`,
  `polygons_png`, `geojson`), `error`.
- `DELETE /analyses/{id}` → `204`; remove linha, mensagens e arquivos.

Storage: `analyses/<user_id>/<analysis_id>/{original.tif, scl.tif, rgb.png,
classification.png, polygons.png, result.geojson}`.

### `stats`

```json
{
  "total_area_ha": 2621.44,
  "valid_area_ha": 2621.44,
  "masked_area_ha": 0.0,
  "potential_area_ha": 0.0,
  "polygon_count": 0,
  "ndvi": {"min": 0.0, "p5": 0.0, "median": 0.0, "p95": 0.0, "max": 0.0},
  "gndvi": {"min": 0.0, "p5": 0.0, "median": 0.0, "p95": 0.0, "max": 0.0},
  "excluded_area_ha": {
    "no_data": 0.0,
    "quality_mask": 0.0,
    "low_vegetation": 0.0,
    "dense_canopy": 0.0,
    "low_chlorophyll": 0.0,
    "small_patch": 0.0
  }
}
```

Invariante: `total_area_ha = potential_area_ha (raster) + Σ excluded_area_ha`.
`potential_area_ha` reportado é a soma dos polígonos (após simplificação), por
isso o teste tolera a diferença da simplificação. `gndvi` é `null` se a T2.3
for cortada. Exclusão por nível é **exclusiva**: o pixel conta só no primeiro
nível que o remove, na ordem N0 → N4.

### Feição do GeoJSON

`id`, `area_ha`, `ndvi_mean`, `gndvi_mean` (ou `null`),
`class: "potential_coffee_area"`, `validated: false` (R2.13).

### `rationale`

Estrutura gerada só a partir de `params`, `stats` e constantes do método; o
chat e a UI leem daqui e não inventam texto técnico.

```json
{
  "summary": "Áreas potenciais de café por regras espectrais em uma única data …",
  "steps": [
    {"level": "N2", "rule": "NDVI >= 0.55", "excluded_ha": 0.0,
     "why": "Remove solo exposto e pasto seco, que têm NDVI baixo na estação seca."}
  ],
  "masks": {"source": "scl", "classes_excluded": [0, 1, 3, 6, 8, 9, 10, 11]},
  "limitations": [
    "Uma única data: não distingue café de outras perenes com o mesmo vigor.",
    "Sem SWIR: separação de mata e eucalipto só pelo teto de NDVI.",
    "Café jovem, esqueletado ou recepado tende a ficar abaixo do piso de NDVI.",
    "Sem gabarito de campo: resultado não validado, sem acurácia."
  ],
  "references": [
    {"key": "parreiras2025", "citation": "Parreiras et al. (2025), Remote Sensing 17(18), 3168",
     "doi": "10.3390/rs17183168", "used_for": "estrutura hierárquica; GNDVI; confusão com eucalipto"}
  ]
}
```

`METHOD_REFERENCES` em `params.py` guarda a lista fixa de referências, para a
justificativa nunca citar algo fora da seção [Referências](#referências).

## Decisões

| Decisão | Alternativa recusada | Motivo |
| --- | --- | --- |
| Cascata de limiares explícitos, inspirada na hierarquia de Parreiras et al. (2025) | Random Forest com amostras do MapBiomas (abordagem de Maskell et al., 2021 e Parreiras et al., 2025) | Auditável e explicável; o kit não tem rótulos, o RF herdaria erros do MapBiomas (30 m, Landsat) e tornaria a verificação circular |
| Processar o arquivo enviado | Modelo pronto Coffee Probability 2026a (Forest Data Partnership) como classificador | O modelo roda no Earth Engine sobre embeddings anuais do AlphaEarth, não sobre o arquivo enviado (violaria C2.2); exige conta no Earth Engine; cobre 2018–2024 e o kit é de 2025. Fica como referência externa de comparação, fora da app |
| Data única da seca | Exigir duas datas | A app recebe um arquivo; a seca já é a época mais informativa entre pasto e perene. A segunda data é opcional (R3.8) |
| Contagem de área por nível de exclusão | Só a máscara final | Fecha uma soma testável e permite ao chat explicar exclusões com números do processamento |
| Sem textura GLCM | GLCM sobre NIR | Em Parreiras et al. (2025) a textura teve importância média menor que bandas e índices; custo e explicação não compensam |
| NDVI + GNDVI (GNDVI condicional) | EVI | GNDVI usa a banda verde (Gitelson et al., 1996) e foi o índice mais importante em Parreiras et al. (2025); EVI tem coeficientes (G, C1, C2, L) a justificar e não tem, nas fontes lidas, evidência específica para café. Condicional porque, no kit, repete o NDVI (r = 0,96) |
| Área calculada em UTM | Área em graus / geodésica no WGS84 | UTM é o CRS nativo em metros; cada pixel = 0,01 ha |
| SCL por vizinho mais próximo | Bilinear | SCL é categórica; interpolar cria classes inexistentes |
| `rasterio` com conversão manual | `rioxarray` com `mask_and_scale=True` | Controle explícito evita a conversão dupla avisada no LEIA-ME |

## Riscos

- Conversão dupla de scale/offset → teste com pixel conhecido (R2.2).
- Mata ciliar e eucalipto entrando como candidato → teto de NDVI; documentar
  antes/depois na nota (é o "erro encontrado" mais provável). Sem SWIR, o
  teto também corta café adensado: declarado em `limitations`.
- Pasto verde, cana ou capoeira na faixa do café → limitação de uma data só;
  mitigação parcial pela amplitude entre datas (R3.8, spec 003).
- GNDVI redundante com o NDVI (r = 0,96 no kit) → decisão condicional na T2.5,
  registrada com o motivo; nada de usar só para "parecer mais completo".
- Overlay deslocado no mapa → bounds calculados a partir do transform e
  reprojetados para WGS84; conferir no mapa (004).
- Memória no Render free (512 MB) → limite de 2048 x 2048 (R6.7) e float32.

## Estratégia de testes

| Requisito | Teste |
| --- | --- |
| R2.1 | `test_pipeline.py`: kit processado de verdade → `completed`; arquivo sintético diferente → estatísticas diferentes (C2.2) |
| R2.2 | `test_reader.py`: DN B04=1100, B08=4100 → reflectância 0,01 e 0,31; NDVI = 0,9375 (conversão dupla daria outro valor); `params.radiometry.source` = `file_tags` ou `kit_default` |
| R2.3 | `test_reader.py`: pixel com DN 0 fica mascarado e fora da área; conta em `excluded_area_ha.no_data` |
| R2.4 | `test_reader.py`: descrições de banda fora de ordem são reordenadas; sem descrição, assume B02, B03, B04, B08 |
| R2.5 | `test_reader.py`: tag `ACQUISITION_UTC` lida; sem a tag → `acquired_at = null` |
| R2.6 | `test_masking.py`: SCL 2x2 sintética → máscara 4x4 com classes certas |
| R2.7 | `test_masking.py`: sem SCL, pixel com NDWI > `ndwi_water_min` vai para `quality_mask` |
| R2.8, R2.9 | `test_indices.py`: valores conhecidos; denominador zero não gera `inf`/`nan` em pixel válido |
| R2.10, R2.11 | `test_classification.py`: raster sintético com faixas de NDVI conhecidas cai em `low_vegetation`, candidato e `dense_canopy`; mancha < 50 px vai para `small_patch`; `gndvi_min = null` não altera o resultado |
| R2.12, R2.14, R2.15 | `test_area.py`: kit → 2.621,44 ha; soma de `area_ha` ≈ pixels candidatos x 0,01 (tolerância da simplificação); `total = potencial + Σ excluded_area_ha` exato no raster |
| R2.13 | `test_vectorization.py`: GeoJSON válido, coordenadas dentro de `area_estudo.geojson`, propriedades obrigatórias presentes |
| R2.16 | `test_render.py`: três PNGs gerados com o tamanho do raster; classificação com alfa 0 fora dos candidatos; inspeção visual na T2.8 |
| R2.17 | `test_pipeline.py`: duas execuções iguais → mesmo GeoJSON e mesmos `stats` |
| R2.18 | `test_rationale.py`: limiares e hectares da justificativa batem com `params` e `stats`; `references` é subconjunto de `METHOD_REFERENCES`; nenhuma frase usa "café detectado" nem percentual de acurácia (C1.1, C1.2) |
| R2.19 | `test_pipeline.py`: arquivo corrompido → `failed` com mensagem legível, sem stack trace |
| R2.20 | `test_pipeline.py`: raster sem vegetação → 0 polígonos, status `completed` |
| R2.21 | `test_isolation.py` (006) |

## Referências

Conferidas em 30/10/2026. A coluna "Conferido" diz o que foi aberto (C5.2).

| Chave | Referência | Conferido |
| --- | --- | --- |
| parreiras2025 | Parreiras, T. C.; Santos, C. de O.; Bolfe, E. L.; Sano, E. E.; Leandro, V. B. S.; Bayma, G.; Silva, L. A. P. da; Furuya, D. E. G.; Romani, L. A. S.; Morton, D. Dense time series of harmonized Landsat Sentinel-2 and ensemble machine learning to map coffee production stages. *Remote Sensing*, 17(18), 3168, 2025. doi:10.3390/rs17183168. CC BY 4.0 | Texto completo (PDF no repositório Alice/Embrapa) |
| maskell2021 | Maskell, G. M.; Chemura, A.; Nguyen, H.; Gornott, C.; Mondal, P. Integration of Sentinel optical and radar data for mapping smallholder coffee production systems in Vietnam. *Remote Sensing of Environment*, 266, 112709, 2021. doi:10.1016/j.rse.2021.112709 | Texto completo (versão aceita no repositório do PIK) |
| souza2019 | Souza, C. G.; Arantes, T. B.; Carvalho, L. M. T. de; Aguiar, P. Variáveis multitemporais para o mapeamento de áreas de cultivo de café. *Pesquisa Agropecuária Brasileira*, 54, 2019. doi:10.1590/S1678-3921.pab2019.v54.00017 | Artigo na SciELO (texto; tabela 1 não conferida) |
| alves2016 | Alves, H. M. R.; Volpato, M. M. L.; Vieira, T. G. C.; Maciel, D. A.; Gonçalves, T. G.; Dantas, M. F. Characterization and spectral monitoring of coffee lands in Brazil. *ISPRS Archives*, XLI-B8, 801–803, 2016. doi:10.5194/isprs-archives-XLI-B8-801-2016 | Página do artigo; NDVI médio de 0,21 a 0,91 em áreas de café no sul de MG (Landsat 8) — não usado para limiar |
| gitelson1996 | Gitelson, A. A.; Kaufman, Y. J.; Merzlyak, M. N. Use of a green channel in remote sensing of global vegetation from EOS-MODIS. *Remote Sensing of Environment*, 58(3), 289–298, 1996. doi:10.1016/S0034-4257(96)00072-7 | Registro bibliográfico e resumo |
| mcfeeters1996 | McFeeters, S. K. The use of the Normalized Difference Water Index (NDWI) in the delineation of open water features. *International Journal of Remote Sensing*, 17(7), 1425–1432, 1996. doi:10.1080/01431169608948714 | Registro bibliográfico; fórmula conferida em fonte secundária |
| rouse1974 | Rouse, J. W. et al. Monitoring vegetation systems in the Great Plains with ERTS, 1974 | **A conferir** antes de entrar na nota |
| fdp2026 | Forest Data Partnership. Coffee Probability model 2026a. Google Earth Engine, `projects/forestdatapartnership/assets/coffee/model_2026a`. CC BY 4.0, atribuição "Produced by Google for the Forest Data Partnership" | Página do catálogo e README do modelo no GitHub (`google/forest-data-partnership`) |
| mapbiomas | Projeto MapBiomas, Coleção 10, classe 46 (Café), 30 m | Legenda conferida em fonte secundária; termos de uso **a conferir** |
| s2scl | Classes da SCL do Sentinel-2 L2A (Sentinel Hub custom scripts) | Página aberta; documento da ESA **a conferir** |
