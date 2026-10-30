---
id: "002"
titulo: Processamento da imagem e classificação de áreas potenciais
status: em-implementacao
---

# 002 — Processamento e classificação: design

## Visão geral

Processamento **em plano de fundo, no próprio processo da API**. O request
valida o arquivo, cria a análise em `processing` e responde `202` na hora; o
pipeline roda numa thread e grava `completed` ou `failed`. O front consulta o
status até a análise sair de `processing` (spec 004).

Motivo: no Render free (~0,1 vCPU, 512 MB, valor a confirmar na T2.11) um
recorte de 2048 x 2048 pode levar minutos, e um request preso esse tempo
deixa a tela sem retorno. O contrato assíncrono já nasce com o front, então
a mudança não custa retrabalho na spec 004.

```text
request:  upload ─> validação (006) ─> cota (006) ─> insert `processing` ─> 202 {id}
thread:   leitura ─> máscara ─> índices ─> regra hierárquica ─> morfologia
          ─> vetorização ─> render ─> storage ─> update `completed` | `failed`
front:    GET /analyses/{id} a cada 2 s enquanto `processing`
```

### Execução em plano de fundo (`worker.py`)

- **Agendamento:** `BackgroundTasks` do FastAPI. A tarefa roda depois que a
  resposta `202` é enviada, numa thread do threadpool do Starlette (o pipeline
  é síncrono e usa CPU, não pode rodar no event loop).
- **Um por vez:** `PROCESSING_SLOT = threading.Semaphore(1)` envolve o
  pipeline. Com 512 MB, dois rasters de 2048 x 2048 em float32 com índices e
  máscaras ao mesmo tempo arriscam estourar a memória. Quem chega depois
  espera na fila do semáforo, ainda em `processing`.
- **Bytes em memória:** o arquivo validado (≤ 20 MB, R6.5) é passado para a
  tarefa como `bytes`; o worker grava `original.tif` e as saídas no storage.
  Não há releitura do storage, o que evita uma ida e volta de rede.
- **Falha:** o worker captura qualquer exceção, registra o stack trace no log
  do servidor e grava `failed` com mensagem legível (R2.19). Nada sobe para o
  cliente, que só vê o `error` da linha.
- **Ordem das escritas:** primeiro o storage, depois o `update` da linha para
  `completed` com `stats`, `params`, `rationale` e `bounds_wgs84`. Assim uma
  análise `completed` sempre tem os arquivos.
- **Análise órfã:** um reinício ou deploy mata a thread e deixa a linha em
  `processing`. Antes de listar ou ler análises, o backend roda um único
  `update analyses set status = 'failed', error = … where user_id = %s and
  status = 'processing' and created_at < now() - stale_after` (padrão 15 min).
  É feito na leitura, e não na subida da API, porque no deploy do Render a
  instância nova sobe antes de a antiga morrer: uma varredura na subida não
  veria as órfãs criadas depois dela.
- **Tempo medido:** o worker registra no log a duração de cada processamento.
  A T2.11 mede o kit em produção, e `stale_after` precisa ficar bem acima do
  pior caso medido.
- **Hibernação:** o Render free dorme após ~15 min sem requisições. Enquanto
  o front consulta o status chegam requisições; se o usuário fechar a aba, o
  processamento termina muito antes desse prazo.
- **Cota:** o upload conta em `usage_daily` (R6.8) quando é aceito, antes do
  `202`. Uma análise que falha depois continua contando: sem isso, um arquivo
  feito para falhar daria processamento ilimitado.

Fila externa (Celery ou RQ com Redis, `pgmq` com worker separado) fica como
evolução: exige um segundo serviço sempre ligado, e worker não existe no plano
free do Render (C4).

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
| `backend/app/processing/errors.py` | `ProcessingError`: erro esperado com mensagem legível ao usuário |
| `backend/app/processing/pipeline.py` | Orquestra e devolve `AnalysisResult` (função pura: bytes e `Params` → resultado, sem banco nem storage) |
| `backend/app/worker.py` | `run_analysis`: semáforo, pipeline, storage, `update` final e captura de falhas; `expire_stale` para órfãs |
| `backend/app/routes/analyses.py` | Endpoints; `POST` valida, cria a linha e agenda `run_analysis` |
| `backend/app/storage.py` | Upload/download no Supabase Storage, URLs assinadas |

## Parâmetros versionados

```json
{
  "method_version": "spectral-rules-1.0",
  "radiometry": {"scale": [0.0001, 0.0001, 0.0001, 0.0001],
                 "offset": [-0.1, -0.1, -0.1, -0.1], "source": "file_tags"},
  "bands": {"indexes": [1, 2, 3, 4], "source": "descriptions"},
  "scl_exclude": [0, 1, 3, 6, 8, 9, 10, 11],
  "ndwi_water_min": 0.0,
  "ndvi_min": 0.55,
  "ndvi_max": 0.72,
  "gndvi_min": null,
  "morphology_iterations": 1,
  "min_area_ha": 0.5,
  "simplify_tolerance_px": 0.5
}
```

Valores finais da calibração (T2.5, 30/10): `ndvi_max` baixou de 0,78 para
0,72 e `gndvi_min` ficou `null` (ver [Resultado](#resultado-da-calibração)). `ndwi_water_min = 0,0` segue a leitura de McFeeters (água positiva).

`radiometry` e `bands` não são escolhas do método: registram o que o leitor
encontrou no arquivo, para a análise ser reproduzível (C2.3). Ambos seguem a
ordem azul, verde, vermelho, NIR.

- `radiometry.source`: `file_tags` quando as quatro bandas têm scale/offset no
  GeoTIFF; senão `kit_default` (0,0001 e −0,1 nas quatro). O rasterio devolve
  `1.0`/`0.0` para banda sem a tag, e esse par é lido como "ausente".
- `bands.source`: `descriptions` quando as descrições das bandas identificam
  sem ambiguidade azul, verde, vermelho e NIR (tokens `B02`/`B2`/`blue`,
  `B03`/`B3`/`green`, `B04`/`B4`/`red`, `B08`/`B8`/`nir`, sem diferenciar
  maiúsculas; `B8A` não conta como NIR); senão `default`, com as bandas 1 a 4.
- NoData: pixel com DN 0 (ou igual ao `nodata` do arquivo) em qualquer uma das
  quatro bandas fica fora de `valid` e com reflectância `NaN`.

### Índices (`indices.py`)

Todos são diferenças normalizadas `(a − b) / (a + b)` em float32:
NDVI = (NIR − vermelho)/(NIR + vermelho), NDWI = (verde − NIR)/(verde + NIR)
(McFeeters) e GNDVI = (NIR − verde)/(NIR + verde).

- Fora de `valid`: `NaN`.
- Pixel válido com `a + b ≤ 1e-6` vale `0` (sem sinal). Com o offset de −0,1
  do L2A, pixel muito escuro (água, sombra) pode ter reflectância zero ou
  negativa; a divisão daria `inf`, `nan` ou um sinal invertido sem sentido.
  `0` não passa em nenhum limiar de vegetação (`ndvi_min`) nem de água
  (`NDWI > ndwi_water_min`).
- Resultado limitado a [−1, 1]: com uma das bandas negativa a razão sai da
  faixa teórica.
- No kit nada disso acontece (exploração de 30/10: reflectância mínima 0,0097,
  nenhum denominador ≤ 0, índices dentro de [−1, 1]); a regra protege outros
  arquivos.

### Máscara de qualidade (`masking.py`)

- Com SCL: `rasterio.warp.reproject` para a grade da imagem (mesmo CRS,
  transform e tamanho) com `Resampling.nearest`. Isso cobre os 20 m da SCL e
  também uma SCL em outro CRS ou com outra extensão. No kit, o resultado é
  exatamente o bloco 2 x 2 de cada pixel da SCL (conferido em 30/10).
- Pixel da imagem sem cobertura da SCL recebe classe 0 (sem dado) e é
  excluído: sem a SCL não há como saber a qualidade dele. SE a SCL não cobrir
  nenhum pixel, ENTÃO `ProcessingError` ("A SCL enviada não cobre a imagem").
  SCL ilegível ou sem CRS também vira `ProcessingError`.
- Sem SCL: exclui o pixel com NDWI `>` `ndwi_water_min`.
- A máscara só marca pixels de `valid`: o NoData já conta em `no_data` (N0) e
  não pode contar de novo em `quality_mask` (N1).

### Cascata e morfologia (`classification.py`)

- **Utilizável** = `valid` e fora da máscara de qualidade.
- **Limiar:** pixel utilizável com `ndvi_min ≤ NDVI ≤ ndvi_max`.
- **Morfologia:** abertura e depois fechamento, `morphology_iterations` vezes,
  com elemento em cruz 3 x 3 (vizinhança 4). A abertura vem primeiro para
  tirar pontos isolados e o anel fino de pixels mistos na borda da mata; o
  fechamento depois preenche falhas pequenas dentro do talhão (entrelinha com
  solo exposto).
- **Bordas da imagem:** o scipy trata o lado de fora como "não candidato", e
  o fechamento apagaria a borda inteira de um talhão que encosta no limite do
  recorte (numa imagem 6 x 6 toda candidata, perde 20 pixels; conferido em
  30/10). Por isso a máscara é estendida pela borda (`np.pad`, modo `edge`)
  em `2 x morphology_iterations` pixels (alcance da abertura somada ao
  fechamento) antes e recortada depois. Com só `1 x`, a abertura apagava a
  faixa estendida e o fechamento não fechava a entrelinha na borda (pego no
  teste da T2.6).
- O fechamento pode ligar pixels fora do limiar, mas nunca NoData nem pixel
  mascarado: o resultado é cortado por **utilizável**.
- **Manchas pequenas:** componentes com vizinhança 4, a mesma que o
  `rasterio.features.shapes` usa na vetorização, para que cada componente vire
  um polígono. Fica o componente com pelo menos
  `ceil(min_area_ha / área do pixel)` pixels (50 no kit).
- **Contagem por nível (exclusiva):** cada pixel recebe um código em
  `levels` (uint8): 0 = área potencial; 1 = `no_data`; 2 = `quality_mask`;
  3 = `low_vegetation`; 4 = `dense_canopy`; 5 = `low_chlorophyll` (só com a
  T2.3); 6 = `small_patch`. Um pixel utilizável fora do resultado final vai
  para o primeiro nível cuja regra o exclui (N2, N3, N3b); se passou nos
  limiares e saiu na morfologia ou por tamanho, vai para `small_patch`. Pixel
  que o fechamento incluiu conta como área potencial. A soma das áreas por
  código é a área total do recorte.
- **Área do pixel:** `|det(transform)|` em m² / 10.000. Exige CRS projetado
  em metros (`ProcessingError` no leitor para CRS geográfico) e recusa Web
  Mercator (EPSG:3857), que é métrico mas distorce a área (cerca de +15% a
  21°S).

### Vetorização e estatísticas (`vectorization.py`)

- **Um polígono por mancha:** rotula a área potencial com vizinhança 4 (a
  mesma da T2.6) e vetoriza os rótulos com `rasterio.features.shapes`
  (`connectivity=4`). Cada componente vira um polígono, com buracos se houver.
- **Área:** `area_ha` = pixels da mancha x área do pixel no CRS projetado da
  imagem (R2.12), antes de qualquer reprojeção.
- **Simplificação:** `shapely.simplify` com tolerância de
  `simplify_tolerance_px` x tamanho do pixel (5 m no kit) e
  `preserve_topology=True`, no CRS projetado. Medido no kit (30/10): com 0,5
  pixel só saem vértices colineares (−31% de vértices, de 11.617 para 7.967) e
  a área desenhada é igual à contagem de pixels; com 0,75 pixel uma mancha
  pequena já muda 8% de área, com 1 pixel, 17%. Fica 0,5.
- **Reprojeção:** `pyproj.Transformer(..., always_xy=True)` para EPSG:4326,
  ordem lon/lat. Anel externo anti-horário e buracos horários (regra da mão
  direita, RFC 7946 §3.1.6), sem membro `crs`, coordenadas com 6 casas
  decimais (cerca de 10 cm, §11.2).
- **Ordem e `id`:** feições ordenadas por área decrescente; `id` de 1 a n. Em
  empate, vale a ordem do rótulo (varredura do raster): mesma entrada, mesmos
  `id` (R2.17).
- **Cantos da imagem:** `corners_wgs84` devolve os 4 cantos do raster em
  WGS84 na ordem do MapLibre (superior-esquerdo, superior-direito,
  inferior-direito, inferior-esquerdo); no kit, batem com
  `area_estudo.geojson`.

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
5. Conferência externa com o MapBiomas 2024 (`--mapbiomas`): fração de
   candidato e NDVI por classe. Só confere a decisão; os limiares **não** são
   ajustados para concordar com ele, senão a comparação da spec 007 perde a
   independência.

### Resultado da calibração

Script `scripts/calibrate_thresholds.py`; figuras e resumos em
`docs/evidencias/calibracao/` (`histogramas.png`, `rgb.jpg`,
`mascara-<rótulo>.jpg`, `resumo-<rótulo>.txt`). Valores sem morfologia (T2.6).

| Variante | Candidato | Mata núcleo | Mata SO | Fragmento | Talhões A | Talhões B |
| --- | --- | --- | --- | --- | --- | --- |
| inicial: NDVI 0,55–0,78 | 801 ha | 38% | 63% | 31% | 74% | 77% |
| alternativa: NDVI 0,55–0,74 | 542 ha | 14% | 46% | 12% | 68% | 67% |
| alternativa: 0,55–0,78 e vermelho ≥ 0,04 | 470 ha | 5% | 31% | 8% | 69% | 64% |
| **final: NDVI 0,55–0,72** | **457 ha** | **7%** | **40%** | **10%** | **64%** | **60%** |

Porcentagem = fração de pixels candidatos em amostras retangulares delimitadas
por inspeção visual do RGB (coordenadas no script). É interpretação visual,
não verdade de campo: serve para comparar variantes, não para medir acerto.

- **Erro encontrado:** com 0,55–0,78, o interior da mata (bloco escuro a leste)
  e as bordas dos fragmentos entravam como candidato. O núcleo da mata tem NDVI
  de 0,71 (p5) a 0,84 (p95); os talhões em curva de nível, de 0,44 a 0,77,
  com mediana 0,64. As faixas se sobrepõem, então nenhum teto separa tudo.
- **Decisão:** teto em 0,72, logo acima do p5 do núcleo da mata. Corta 93% do
  núcleo e perde parte do topo dos talhões (de 74–77% para 60–64%). A mata
  mais clara a sudoeste continua com 40%: limitação declarada.
- **Alternativa recusada:** exigir vermelho ≥ 0,04 separa um pouco melhor
  (o dossel fechado absorve o vermelho; o café na seca deixa solo exposto entre
  linhas), mas o ganho visível foi pequeno e seria um limiar empírico sem
  referência conferida, num nível novo da regra.
- **GNDVI:** `gndvi_min = null`. Correlação com o NDVI de 0,97 nos pixels
  válidos, e o histograma 2D não mostra grupo que o GNDVI separe e o NDVI não.
  Continua calculado e reportado (R2.9).
- **Piso:** `ndvi_min = 0,55` mantido, no vale entre o pico de pasto seco
  (~0,30) e o de dossel (~0,80).
- **Conferência com o MapBiomas 2024** (`mapbiomas-inicial.jpg`,
  `mapbiomas-final.jpg`; tabela nos resumos). Feita depois da decisão, sem
  mudar os limiares:

  | Classe MapBiomas 2024 | Área no recorte | Candidato 0,55–0,78 | Candidato 0,55–0,72 | NDVI p5 / mediana / p95 |
  | --- | --- | --- | --- | --- |
  | Formação Florestal | 907 ha | 42% | 13% | 0,60 / 0,79 / 0,84 |
  | Mosaico de Usos | 564 ha | 43% | 33% | 0,22 / 0,54 / 0,78 |
  | Pastagem | 470 ha | 9% | 8% | 0,20 / 0,34 / 0,60 |
  | Café | 49 ha | 61% | 48% | 0,29 / 0,63 / 0,79 |

  A mata do MapBiomas confirma o corte (de 42% para 13% de candidato). O café
  do MapBiomas tem mediana de NDVI 0,63, igual à dos talhões delimitados na
  imagem (0,64), e o maior bloco dele cai sobre a amostra "talhões A". O p95
  de 0,79 mostra o custo do teto: café mais vigoroso fica de fora. Limites da
  conferência: 30 m (Landsat), ano 2024 contra imagem de agosto de 2025, só
  49 ha de café mapeados (boa parte deve estar em "Mosaico de Usos") e erros
  próprios do MapBiomas. É concordância, não acurácia.
- **Sobra para a T2.6:** anel de pixels mistos na borda dos fragmentos de mata,
  com um a dois pixels de largura; a abertura morfológica deve remover a maior
  parte.
- **Com a cascata da T2.6** (abertura, fechamento e manchas ≥ 0,5 ha), a área
  potencial do kit é **214,54 ha** (de 457 ha sem morfologia). Conferência com
  o MapBiomas 2024, refeita com a regra real e sem mudar parâmetros:

  | Classe MapBiomas 2024 | Sem morfologia | Com morfologia |
  | --- | --- | --- |
  | Formação Florestal (907 ha) | 13% | 5% |
  | Mosaico de Usos (564 ha) | 33% | 15% |
  | Outras Lavouras Temporárias (342 ha) | 20% | 12% |
  | Pastagem (470 ha) | 8% | 2% |
  | Café (49 ha) | 48% | 42% |

  Da área marcada, 10% cai em café do MapBiomas (5% sem morfologia), e 42% do
  café dele fica marcado. O que sobra fora do café do MapBiomas está sobretudo
  em Mosaico de Usos, onde pode haver café pequeno demais para 30 m, e em
  lavoura temporária e cana, que uma única data de agosto não separa de café
  (ver amplitude entre datas, R3.8). Concordância baixa e declarada: o
  resultado é triagem por vigor, não mapa de café.

## Contratos

- `POST /analyses` — `multipart/form-data`: `image` (obrigatório), `scl`
  (opcional). → `202 {"id", "status": "processing"}` com cabeçalho
  `Location: /analyses/{id}`; erros 400/413/415/422/429 (006) saem na hora,
  antes do `202`.
- `GET /analyses` → lista do usuário: `id`, `filename`, `created_at`,
  `status`, `acquired_at`, `stats.potential_area_ha` (`null` enquanto
  `processing`).
- `GET /analyses/{id}` → `id`, `status`, `filename`, `created_at`,
  `acquired_at`, `crs`, `bounds_wgs84` (`[[lon,lat] x 4]`), `stats`, `params`,
  `method_version`, `rationale`, `urls` assinadas (`rgb_png`,
  `classification_png`, `polygons_png`, `geojson`), `error`. Enquanto
  `processing`, os campos do resultado e `urls` vêm `null`; o front usa
  `created_at` para mostrar o tempo decorrido.
- `DELETE /analyses/{id}` → `204`; remove linha, mensagens e arquivos. Em
  `processing` → `409` ("Aguarde o fim do processamento"): apagar no meio
  deixaria o worker gravando arquivos de uma análise que não existe mais.
  Uma órfã vira `failed` após `stale_after` e pode ser apagada.

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

Invariante: `total_area_ha = potential_area_ha + Σ excluded_area_ha`.
`valid_area_ha` = total − `no_data`; `masked_area_ha` = `quality_mask`.
`potential_area_ha` é a contagem de pixels da área potencial x área do pixel,
o mesmo número que fecha a soma; `area_ha` de cada feição também vem dos pixels
dela, então a soma das feições é exatamente `potential_area_ha`. A
simplificação só muda o desenho (ver Vetorização). Áreas arredondadas a 2
casas, índices a 4. `ndvi` resume os pixels de `valid`. `gndvi` é `null` até a
T2.3 (ou se ela for cortada). Exclusão por nível é **exclusiva**: o pixel conta só no primeiro
nível que o remove, na ordem N0 → N4.

### Feição do GeoJSON

`id`, `area_ha`, `ndvi_mean`, `gndvi_mean` (ou `null`),
`class: "potential_coffee_area"`, `validated: false` (R2.13). O `id` vai no
`Feature` (RFC 7946) e repetido em `properties`, onde o MapLibre e a ferramenta
`get_polygon` do chat o leem.

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
| Processamento em plano de fundo no processo da API (`BackgroundTasks` + semáforo) | Síncrono no request; fila externa com worker separado | Síncrono prende o request por minutos no Render free; fila externa exige serviço pago (C4). A thread morre num reinício, o que é coberto pela expiração de órfãs |
| Expirar órfãs na leitura | Varredura na subida da API | No deploy do Render a instância nova sobe antes de a antiga morrer; a varredura na subida perderia as órfãs criadas depois dela |
| `409` ao apagar análise em `processing` | Worker detectar a linha apagada e limpar o storage | Uma regra simples no `DELETE` evita corrida entre o worker e a remoção |

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
- Memória no Render free (512 MB) → limite de 2048 x 2048 (R6.7), float32 e
  um processamento por vez (R2.23).
- Thread morta em reinício ou deploy deixa análise presa em `processing` →
  expiração na leitura (R2.24); o front mostra a mensagem e oferece reenviar.
- CPU do Render free mais lenta que o esperado → tempo do kit medido em
  produção na T2.11 e registrado; `stale_after` ajustado a partir dele.

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
| R2.12, R2.14, R2.15 | `test_area.py`: kit → 2.621,44 ha; soma de `area_ha` = `potential_area_ha` = pixels x 0,01; `total = potencial + Σ excluded_area_ha`; área do polígono simplificado igual à contagem de pixels; `valid_area_ha` e `masked_area_ha` com NoData e máscara |
| R2.13 | `test_vectorization.py`: GeoJSON válido (polígonos válidos, anel externo anti-horário, lon/lat), coordenadas dentro de `area_estudo.geojson`, propriedades obrigatórias, `id` por área decrescente, resultado vazio = `FeatureCollection` sem feições; cantos do kit iguais aos de `area_estudo.geojson` |
| R2.16 | `test_render.py`: três PNGs gerados com o tamanho do raster; classificação com alfa 0 fora dos candidatos; inspeção visual na T2.8 |
| R2.17 | `test_pipeline.py`: duas execuções iguais → mesmo GeoJSON e mesmos `stats` |
| R2.18 | `test_rationale.py`: limiares e hectares da justificativa batem com `params` e `stats`; `references` é subconjunto de `METHOD_REFERENCES`; nenhuma frase usa "café detectado" nem percentual de acurácia (C1.1, C1.2) |
| R2.19 | `test_pipeline.py`: arquivo corrompido → `ProcessingError` com mensagem legível (o worker grava como `error`) |
| R2.20 | `test_pipeline.py`: raster sem vegetação → 0 polígonos, status `completed` |
| R2.21 | `test_isolation.py` (006) |
| R2.1, R2.22 | `test_analyses_api.py` (banco e storage substituídos por fakes via dependências do FastAPI): `POST` → `202` com `processing` e `Location`; o `TestClient` roda a tarefa após a resposta, e o `GET` seguinte mostra `completed` |
| R2.19 | `test_worker.py`: pipeline que lança exceção → linha `failed` com mensagem legível; o texto da exceção não aparece em `error` |
| R2.23 | `test_worker.py`: com o semáforo ocupado, a segunda execução espera até a primeira liberar |
| R2.24 | `test_analyses_api.py`: linha em `processing` com `created_at` antigo vira `failed` no `GET`; recente continua `processing` |
| R2.25 | `test_analyses_api.py`: `DELETE` em `processing` → `409`; em `failed` → `204` |

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
| mapbiomas | Projeto MapBiomas – Coleção 10 da Série Anual de Mapas de Cobertura e Uso da Terra do Brasil, ano 2024, classe 46 (Café), 30 m. CC BY 4.0. Lido do COG hospedado no Source Cooperative (`data.source.coop/tristangruppwri/mapbiomas/mapbiomas-brazil`), cujo produtor declarado é o MapBiomas | Legenda da Coleção 10 (PDF oficial) e classe 46 conferidas; licença CC BY 4.0 conferida no rodapé de `brasil.mapbiomas.org/downloads/` em 30/10/2026 ("uso público, aberto e gratuito mediante referência"). A cópia no Source Cooperative declara CC-BY-SA-4.0: vale a licença do produtor. Formato da citação vem da página de perguntas frequentes, que estava fora do ar (404) na consulta |
| s2scl | Classes da SCL do Sentinel-2 L2A (Sentinel Hub custom scripts) | Página aberta; documento da ESA **a conferir** |
