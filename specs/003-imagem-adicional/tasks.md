---
id: "003"
titulo: Imagem adicional e comparação entre datas
status: rascunho
---

# 003 — Imagem adicional e comparação entre datas: tarefas

Bloco do dia: 13h às 14h. Corte se estourar: regra temporal na app (fica na nota e no vídeo).

- [ ] **T3.1** (P0) Script de busca e download no formato do kit, com SCL.
  - _Req: R3.1, R3.2, R3.3, R3.4_
  - Arquivos: `scripts/download_additional_scene.py`
  - Verificação: TIFF com shape (4, 512, 512), CRS e transform iguais ao kit.
- [ ] **T3.2** (P0) Atribuição, metadados e SHA256 da cena adicional.
  - _Req: R3.5_
  - Arquivos: `data/adicional/<item_id>/`
  - Verificação: `sha256sum -c SHA256SUMS.txt`.
- [ ] **T3.3** (P0) Processar a imagem adicional pela aplicação.
  - _Req: R3.6_
  - Verificação: análise `completed` em produção; print em `docs/evidencias/`.
- [ ] **T3.4** (P0) Script de comparação entre datas.
  - _Req: R3.7_
  - Arquivos: `scripts/compare_dates.py`, `docs/evidencias/comparacao-datas.*`
  - Verificação: tabela e figura geradas.
- [ ] **T3.5** (P1) Regra temporal de amplitude no backend.
  - _Req: R3.8_
  - Arquivos: `backend/app/processing/temporal.py`, `backend/tests/test_temporal.py`
  - Verificação: `pytest backend/tests/test_temporal.py`.
