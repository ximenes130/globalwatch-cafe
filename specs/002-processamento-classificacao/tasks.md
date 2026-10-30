---
id: "002"
titulo: Processamento da imagem e classificação de áreas potenciais
status: rascunho
---

# 002 — Processamento e classificação: tarefas

Bloco do dia: 10h às 13h. Corte se estourar: GNDVI (fica só NDVI).

- [ ] **T2.1** (P0) `params.py` e `leitura.py` com conversão única, NoData e data de aquisição.
  - _Req: R2.2, R2.3, R2.4, R2.5_
  - Arquivos: `backend/app/processing/params.py`, `backend/app/processing/leitura.py`, `backend/tests/test_leitura.py`
  - Verificação: `pytest backend/tests/test_leitura.py`.
- [ ] **T2.2** (P0) `indices.py` (NDVI, NDWI) com divisão segura.
  - _Req: R2.8_
  - Arquivos: `backend/app/processing/indices.py`, `backend/tests/test_indices.py`
  - Verificação: `pytest backend/tests/test_indices.py`.
- [ ] **T2.3** (P1) GNDVI em `indices.py` e uso opcional na regra.
  - _Req: R2.9_
  - Verificação: `pytest backend/tests/test_indices.py`.
- [ ] **T2.4** (P0) `mascara.py`: SCL reamostrada e NDWI como fallback.
  - _Req: R2.6, R2.7_
  - Arquivos: `backend/app/processing/mascara.py`, `backend/tests/test_mascara.py`
  - Verificação: `pytest backend/tests/test_mascara.py`.
- [ ] **T2.5** (P0) Calibrar limiares com o kit (histograma + inspeção visual) e registrar valores no `design.md`.
  - _Req: R2.10_
  - Arquivos: `scripts/calibrar_limiares.py`, `docs/evidencias/`
  - Verificação: histograma e máscara salvos em `docs/evidencias/`; valores atualizados em `params.py`.
- [ ] **T2.6** (P0) `classificacao.py`: regra, morfologia e remoção de manchas pequenas.
  - _Req: R2.10, R2.11_
  - Arquivos: `backend/app/processing/classificacao.py`, `backend/tests/test_classificacao.py`
  - Verificação: `pytest backend/tests/test_classificacao.py`.
- [ ] **T2.7** (P0) `vetorizacao.py`: polígonos, área em UTM, GeoJSON RFC 7946, estatísticas.
  - _Req: R2.12, R2.13, R2.14, R2.15_
  - Arquivos: `backend/app/processing/vetorizacao.py`, `backend/tests/test_area.py`, `backend/tests/test_vetorizacao.py`
  - Verificação: `pytest backend/tests/test_area.py backend/tests/test_vetorizacao.py` (2.621,44 ha).
- [ ] **T2.8** (P0) `render.py`: PNG RGB, classificação e polígonos.
  - _Req: R2.16_
  - Arquivos: `backend/app/processing/render.py`
  - Verificação: abrir os PNGs gerados do kit; salvar cópia em `docs/evidencias/`.
- [ ] **T2.9** (P0) `justificativa.py` e `pipeline.py` com status `erro` e resultado vazio.
  - _Req: R2.17, R2.18, R2.19, R2.20_
  - Arquivos: `backend/app/processing/justificativa.py`, `backend/app/processing/pipeline.py`, `backend/tests/test_pipeline.py`
  - Verificação: `pytest backend/tests/test_pipeline.py`.
- [ ] **T2.10** (P0) `storage.py` e rotas `/analyses` (POST, GET lista, GET id, DELETE).
  - _Req: R2.1, R2.21_
  - Arquivos: `backend/app/storage.py`, `backend/app/routes/analyses.py`
  - Verificação: `curl -F imagem=@data/exemplo/imagem_multiespectral.tif` em produção com token; resposta com stats do kit.
