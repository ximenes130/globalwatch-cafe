---
id: "003"
titulo: Imagem adicional e comparação entre datas
status: em-implementacao
---

# 003 — Imagem adicional e comparação entre datas: tarefas

Bloco do dia: 13h às 14h. Corte se estourar: a regra temporal na app (T3.5)
fica na nota e no vídeo. A T3.5 entra nesta rodada, por decisão do usuário na
aprovação.

- [x] **T3.1** (P0) Script de busca, escolha e download no formato do kit, com SCL.
  - _Req: R3.1, R3.2, R3.3, R3.4, R3.5_
  - Arquivos: `scripts/download_additional_scene.py`
  - Verificação: lista de candidatas com fração de problema no recorte; TIFF com
    shape (4, 512, 512), CRS e transform iguais aos do kit; `read_image` aceita
    o arquivo e a área total é 2.621,44 ha; `--item` de outro tile para sem
    gravar.
- [x] **T3.2** (P0) Atribuição, metadados e SHA256 da cena adicional, versionados.
  - _Req: R3.6_
  - Arquivos: `data/adicional/<item_id>/`
  - Verificação: `sha256sum -c SHA256SUMS.txt`.
- [x] **T3.3** (P0) Script de comparação entre datas e registro na nota de pesquisa.
  - _Req: R3.8, R3.9_
  - Arquivos: `scripts/compare_dates.py`,
    `docs/evidencias/comparacao-datas/{resumo.txt,comparacao.jpg}`,
    `docs/nota-de-pesquisa.md`
  - Verificação: tabela e figura geradas; soma das transições igual à base
    comum.
- [ ] **T3.4** (P0) Processar a imagem adicional pela aplicação em produção.
  - _Req: R3.7_
  - Arquivos: `scripts/smoke_analysis.sh` (variáveis `IMAGE` e `SCL`)
  - Verificação: análise `completed` em produção, com área potencial e
    polígonos iguais aos do `resumo.txt`. Depende da chave do Storage no
    Render (T2.11) e de um token do usuário.
- [ ] **T3.5** (P1) Regra temporal de amplitude no backend.
  - _Req: R3.10_
  - Arquivos: `backend/app/processing/temporal.py`, `backend/tests/test_temporal.py`
  - Verificação: `pytest backend/tests/test_temporal.py`.
