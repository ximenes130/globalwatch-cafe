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
upload ─> validação (006) ─> leitura ─> máscara ─> índices ─> regra
       ─> morfologia ─> vetorização ─> render ─> storage + linha em analyses
```

## Componentes e arquivos

| Arquivo | Responsabilidade |
| --- | --- |
| `backend/app/processing/reader.py` | Abre o raster (MemoryFile), aplica scale/offset uma vez, máscara de NoData, lê data e CRS |
| `backend/app/processing/masking.py` | SCL (vizinho mais próximo, classes excluídas) ou NDWI |
| `backend/app/processing/indices.py` | NDVI, GNDVI, NDWI com divisão segura |
| `backend/app/processing/classification.py` | Regra de candidato, morfologia (`scipy.ndimage`), remoção de manchas pequenas |
| `backend/app/processing/vectorization.py` | `rasterio.features.shapes`, simplificação, área em UTM, reprojeção para WGS84 |
| `backend/app/processing/render.py` | PNG RGB (realce p2–p98), PNG da classificação, PNG com polígonos |
| `backend/app/processing/rationale.py` | Monta a justificativa estruturada |
| `backend/app/processing/params.py` | `Params` (dataclass/pydantic) + `METHOD_VERSION` |
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

Valores finais definidos na calibração (T2.5) e registrados aqui.

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

## Decisões

| Decisão | Alternativa recusada | Motivo |
| --- | --- | --- |
| Regras espectrais com parâmetros explícitos | Random Forest com amostras do MapBiomas | Auditável e explicável; RF herdaria erros do MapBiomas e tornaria a verificação circular |
| Área calculada em UTM | Área em graus / geodésica no WGS84 | UTM é o CRS nativo em metros; cada pixel = 0,01 ha |
| SCL por vizinho mais próximo | Bilinear | SCL é categórica; interpolar cria classes inexistentes |
| `rasterio` com conversão manual | `rioxarray` com `mask_and_scale=True` | Controle explícito evita a conversão dupla avisada no LEIA-ME |
| NDVI + GNDVI | EVI | GNDVI é mais simples, usa a banda verde disponível e satura menos em dossel denso |

## Riscos

- Conversão dupla de scale/offset → teste com pixel conhecido (R2.2).
- Mata ciliar e eucalipto entrando como candidato → limite superior de NDVI;
  documentar antes/depois na nota (é o "erro encontrado" mais provável).
- Overlay deslocado no mapa → bounds calculados a partir do transform e
  reprojetados para WGS84; conferir no mapa (004).
- Memória no Render free (512 MB) → limite de 2048 x 2048 (R6.7) e float32.

## Estratégia de testes

| Requisito | Teste |
| --- | --- |
| R2.2 | `test_reader.py`: DN B04=1100, B08=4100 → reflectância 0,01 e 0,31; NDVI = 0,9375 (conversão dupla daria outro valor) |
| R2.3 | `test_reader.py`: pixel com DN 0 fica mascarado e fora da área |
| R2.6 | `test_masking.py`: SCL 2x2 sintética → máscara 4x4 com classes certas |
| R2.8–R2.11 | `test_classification.py`: raster sintético com faixas de NDVI conhecidas; mancha < 50 px removida |
| R2.12, R2.14, R2.15 | `test_area.py`: kit → 2.621,44 ha; soma de `area_ha` ≈ pixels candidatos x 0,01 (tolerância da simplificação) |
| R2.13 | `test_vectorization.py`: GeoJSON válido, coordenadas dentro de `area_estudo.geojson` |
| R2.17 | `test_pipeline.py`: duas execuções iguais → mesmo GeoJSON |
| R2.20 | `test_pipeline.py`: raster sem vegetação → 0 polígonos, status `completed` |
| R2.21 | `test_isolation.py` (006) |
