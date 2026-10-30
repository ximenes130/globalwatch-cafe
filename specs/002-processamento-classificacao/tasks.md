---
id: "002"
titulo: Processamento da imagem e classificação de áreas potenciais
status: rascunho
---

# 002 — Processamento e classificação: tarefas

Bloco do dia: 10h às 13h. Corte se estourar: GNDVI (fica só NDVI).

- [ ] **T2.1** (P0) `params.py` e `reader.py` com conversão única, NoData, ordem das bandas e data de aquisição.
  - _Req: R2.2, R2.3, R2.4, R2.5_
  - Arquivos: `backend/app/processing/params.py`, `backend/app/processing/reader.py`, `backend/tests/test_reader.py`
  - Verificação: `pytest backend/tests/test_reader.py` (pixel conhecido → NDVI 0,9375; DN 0 mascarado; bandas reordenadas pela descrição; `ACQUISITION_UTC` ausente → `null`).
- [ ] **T2.2** (P0) `indices.py` (NDVI, NDWI) com divisão segura.
  - _Req: R2.8_
  - Arquivos: `backend/app/processing/indices.py`, `backend/tests/test_indices.py`
  - Verificação: `pytest backend/tests/test_indices.py` (valores conhecidos; denominador zero sem `inf`/`nan` em pixel válido).
- [ ] **T2.3** (P1) GNDVI em `indices.py`, estatísticas, `gndvi_mean` por feição e condição opcional `gndvi_min` na regra.
  - _Req: R2.9, R2.13, R2.14_
  - Verificação: `pytest backend/tests/test_indices.py backend/tests/test_classification.py` (`gndvi_min = null` não altera o resultado).
- [ ] **T2.4** (P0) `masking.py`: SCL reamostrada e NDWI como fallback.
  - _Req: R2.6, R2.7_
  - Arquivos: `backend/app/processing/masking.py`, `backend/tests/test_masking.py`
  - Verificação: `pytest backend/tests/test_masking.py`.
- [ ] **T2.5** (P0) Calibrar limiares com o kit pelo procedimento do design e registrar os valores finais no `design.md`.
  - _Req: R2.9, R2.10_
  - Arquivos: `scripts/calibrate_thresholds.py`, `docs/evidencias/`
  - Passos: (1) histograma de NDVI e GNDVI com os limiares marcados; (2) máscara sobre o RGB, conferindo talhões, mata ciliar e eucalipto; (3) decisão sobre `gndvi_min` registrada com o motivo; (4) antes/depois do ajuste salvo para o "erro encontrado" da nota.
  - Verificação: histogramas, máscaras e antes/depois em `docs/evidencias/`; valores atualizados em `params.py`, no `design.md` e em `frontend/src/lib/method.ts` (régua do login). Sem percentual de acerto.
- [ ] **T2.6** (P0) `classification.py`: cascata N2–N4 (limiares, morfologia, manchas pequenas) com área excluída por nível.
  - _Req: R2.10, R2.11, R2.14_
  - Arquivos: `backend/app/processing/classification.py`, `backend/tests/test_classification.py`
  - Verificação: `pytest backend/tests/test_classification.py` (faixas sintéticas caem em `low_vegetation`, candidato e `dense_canopy`; mancha < 50 px em `small_patch`; cada pixel contado em um só nível).
- [ ] **T2.7** (P0) `vectorization.py`: polígonos, área em UTM, GeoJSON RFC 7946, estatísticas.
  - _Req: R2.12, R2.13, R2.14, R2.15_
  - Arquivos: `backend/app/processing/vectorization.py`, `backend/tests/test_area.py`, `backend/tests/test_vectorization.py`
  - Verificação: `pytest backend/tests/test_area.py backend/tests/test_vectorization.py` (kit = 2.621,44 ha; total = potencial no raster + Σ `excluded_area_ha`; propriedades obrigatórias nas feições).
- [ ] **T2.8** (P0) `render.py`: PNG RGB, classificação e polígonos.
  - _Req: R2.16_
  - Arquivos: `backend/app/processing/render.py`, `backend/tests/test_render.py`
  - Verificação: `pytest backend/tests/test_render.py` (tamanho do raster; alfa 0 fora dos candidatos); abrir os PNGs do kit e salvar cópia em `docs/evidencias/`.
- [ ] **T2.9** (P0) `rationale.py` (com `METHOD_REFERENCES`) e `pipeline.py` com status `failed` e resultado vazio.
  - _Req: R2.1, R2.17, R2.18, R2.19, R2.20_
  - Arquivos: `backend/app/processing/rationale.py`, `backend/app/processing/params.py`, `backend/app/processing/pipeline.py`, `backend/tests/test_rationale.py`, `backend/tests/test_pipeline.py`
  - Verificação: `pytest backend/tests/test_rationale.py backend/tests/test_pipeline.py` (números da justificativa batem com `params`/`stats`; referências só da lista fixa; sem "café detectado" nem percentual de acurácia; duas execuções iguais → mesmo resultado; arquivo diferente → stats diferentes; arquivo corrompido → `failed` sem stack trace; sem vegetação → 0 polígonos).
- [ ] **T2.10** (P0) `storage.py` e rotas `/analyses` (POST, GET lista, GET id, DELETE).
  - _Req: R2.1, R2.21_
  - Arquivos: `backend/app/storage.py`, `backend/app/routes/analyses.py`
  - Verificação: `curl -F image=@data/exemplo/imagem_multiespectral.tif` em produção com token; resposta com stats do kit.
