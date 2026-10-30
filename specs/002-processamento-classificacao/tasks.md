---
id: "002"
titulo: Processamento da imagem e classificação de áreas potenciais
status: em-implementacao
---

# 002 — Processamento e classificação: tarefas

Bloco do dia: 10h às 13h. Corte se estourar: GNDVI (fica só NDVI).

- [x] **T2.1** (P0) `params.py` e `reader.py` com conversão única, NoData, ordem das bandas e data de aquisição.
  - _Req: R2.2, R2.3, R2.4, R2.5_
  - Arquivos: `backend/app/processing/params.py`, `backend/app/processing/reader.py`, `backend/app/processing/errors.py`, `backend/tests/test_reader.py`
  - Verificação: `pytest backend/tests/test_reader.py` (pixel conhecido → NDVI 0,9375; DN 0 mascarado; bandas reordenadas pela descrição; `ACQUISITION_UTC` ausente → `null`).
- [x] **T2.2** (P0) `indices.py` (NDVI, NDWI) com divisão segura.
  - _Req: R2.8_
  - Arquivos: `backend/app/processing/indices.py`, `backend/tests/test_indices.py`
  - Verificação: `pytest backend/tests/test_indices.py` (valores conhecidos; denominador zero sem `inf`/`nan` em pixel válido).
- [x] **T2.4** (P0) `masking.py`: SCL reamostrada e NDWI como fallback.
  - _Req: R2.6, R2.7_
  - Arquivos: `backend/app/processing/masking.py`, `backend/tests/test_masking.py`
  - Verificação: `pytest backend/tests/test_masking.py`.
- [x] **T2.5** (P0) Calibrar limiares com o kit pelo procedimento do design e registrar os valores finais no `design.md`.
  - _Req: R2.9, R2.10_
  - Arquivos: `scripts/calibrate_thresholds.py`, `docs/evidencias/`
  - Passos: (1) histograma de NDVI e GNDVI com os limiares marcados; (2) máscara sobre o RGB, conferindo talhões, mata ciliar e eucalipto; (3) decisão sobre `gndvi_min` registrada com o motivo; (4) antes/depois do ajuste salvo para o "erro encontrado" da nota; (5) conferência com o MapBiomas 2024, sem ajustar os limiares a ele.
  - Verificação: histogramas, máscaras e antes/depois em `docs/evidencias/`; valores atualizados em `params.py`, no `design.md` e em `frontend/src/lib/method.ts` (régua do login). Sem percentual de acerto.
- [x] **T2.6** (P0) `classification.py`: cascata N2–N4 (limiares, morfologia, manchas pequenas) com área excluída por nível.
  - _Req: R2.10, R2.11, R2.14_
  - Arquivos: `backend/app/processing/classification.py`, `backend/app/processing/reader.py` (área do pixel e CRS), `backend/pyproject.toml` (scipy), `backend/tests/test_classification.py`, `backend/tests/test_reader.py`
  - Verificação: `pytest backend/tests/test_classification.py` (faixas sintéticas caem em `low_vegetation`, candidato e `dense_canopy`; mancha < 50 px em `small_patch`; cada pixel contado em um só nível).
- [ ] **T2.7** (P0) `vectorization.py`: polígonos, área em UTM, GeoJSON RFC 7946, estatísticas.
  - _Req: R2.12, R2.13, R2.14, R2.15_
  - Arquivos: `backend/app/processing/vectorization.py`, `backend/tests/test_area.py`, `backend/tests/test_vectorization.py`
  - Verificação: `pytest backend/tests/test_area.py backend/tests/test_vectorization.py` (kit = 2.621,44 ha; total = potencial no raster + Σ `excluded_area_ha`; propriedades obrigatórias nas feições).
- [ ] **T2.3** (P1) GNDVI em `indices.py`, estatísticas, `gndvi_mean` por feição e condição opcional `gndvi_min` na regra. Feita depois da T2.7 porque depende de `classification.py` e `vectorization.py`.
  - _Req: R2.9, R2.13, R2.14_
  - Verificação: `pytest backend/tests/test_indices.py backend/tests/test_classification.py` (`gndvi_min = null` não altera o resultado).
- [ ] **T2.8** (P0) `render.py`: PNG RGB, classificação e polígonos.
  - _Req: R2.16_
  - Arquivos: `backend/app/processing/render.py`, `backend/tests/test_render.py`
  - Verificação: `pytest backend/tests/test_render.py` (tamanho do raster; alfa 0 fora dos candidatos); abrir os PNGs do kit e salvar cópia em `docs/evidencias/`.
- [ ] **T2.9** (P0) `rationale.py` (com `METHOD_REFERENCES`) e `pipeline.py` como função pura, com erro legível e resultado vazio.
  - _Req: R2.1, R2.17, R2.18, R2.19, R2.20_
  - Arquivos: `backend/app/processing/rationale.py`, `backend/app/processing/params.py`, `backend/app/processing/pipeline.py`, `backend/tests/test_rationale.py`, `backend/tests/test_pipeline.py`
  - Verificação: `pytest backend/tests/test_rationale.py backend/tests/test_pipeline.py` (números da justificativa batem com `params`/`stats`; referências só da lista fixa; sem "café detectado" nem percentual de acurácia; duas execuções iguais → mesmo resultado; arquivo diferente → stats diferentes; arquivo corrompido → `ProcessingError` com mensagem legível; sem vegetação → 0 polígonos).
- [ ] **T2.10** (P0) `storage.py` e `worker.py`: `run_analysis` com semáforo, escrita no storage antes do `update` final, captura de falhas e log da duração; `expire_stale` para órfãs.
  - _Req: R2.1, R2.16, R2.19, R2.23, R2.24_
  - Arquivos: `backend/app/storage.py`, `backend/app/worker.py`, `backend/tests/test_worker.py`
  - Verificação: `pytest backend/tests/test_worker.py` (exceção no pipeline → `failed` sem o texto da exceção; semáforo ocupado faz a segunda execução esperar; `expire_stale` só afeta `processing` antigas do próprio usuário).
- [ ] **T2.11** (P0) Rotas `/analyses`: `POST` com `202` e agendamento, `GET` lista e id com expiração de órfãs, `DELETE` com `409` em `processing`.
  - _Req: R2.1, R2.21, R2.22, R2.24, R2.25_
  - Arquivos: `backend/app/routes/analyses.py`, `backend/app/main.py`, `backend/tests/test_analyses_api.py`
  - Verificação: `pytest backend/tests/test_analyses_api.py`; em produção, `curl -F image=@data/exemplo/imagem_multiespectral.tif` com token → `202`, consulta até `completed` com os stats do kit; duração do processamento lida no log do Render e registrada em `docs/evidencias/` e no `design.md` (base de `stale_after`).
