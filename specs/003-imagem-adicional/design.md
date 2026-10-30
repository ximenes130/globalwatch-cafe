---
id: "003"
titulo: Imagem adicional e comparação entre datas
status: rascunho
---

# 003 — Imagem adicional e comparação entre datas: design

## Visão geral

```text
pystac-client ─> busca (bbox da área, datas, eo:cloud_cover) ─> item
   └─> rasterio lê COGs B02/B03/B04/B08 com window da grade do kit
   └─> empilha uint16 + tags ─> data/adicional/<item_id>/imagem_multiespectral.tif
   └─> SCL recortada ─> data/adicional/<item_id>/qualidade_scl.tif
   └─> ATRIBUICAO.txt, metadados.json, SHA256SUMS.txt
```

A grade de referência vem do próprio `data/exemplo/imagem_multiespectral.tif`
(transform, largura, altura). Como o kit e a cena nova estão no mesmo tile
MGRS (23KLS), a leitura é por janela, sem reamostragem.

## Componentes e arquivos

| Arquivo | Responsabilidade |
| --- | --- |
| `scripts/download_additional_scene.py` | Busca, recorte, empilhamento, tags, atribuição |
| `scripts/compare_dates.py` | Lê os dois GeoJSON/rasters e gera tabela e figura de variação |
| `data/adicional/<item_id>/` | Saída versionada (arquivos pequenos) |
| `backend/app/processing/temporal.py` | *(P1)* regra de amplitude |

## Contratos

- CLI: `python scripts/download_additional_scene.py --start 2026-01-01 --end
  2026-03-31 --max-cloud 10 [--item <id>]`.
- *(P1)* `POST /analyses` aceita `image_2` opcional; exige mesmo CRS e mesma
  grade, senão 422.

## Decisões

| Decisão | Alternativa recusada | Motivo |
| --- | --- | --- |
| Earth Search (mesma fonte do kit) | Copernicus Data Space; Google Earth Engine | Sem autenticação e mesmo processamento L2A do kit; GEE exige conta e tem restrição de uso |
| Mesmo tile e grade do kit | Reprojetar para outra grade | Comparação pixel a pixel sem reamostragem |
| Scale/offset do STAC | Valores fixos | O offset depende do processing baseline |

## Riscos

- Nuvem na estação chuvosa → escolher a melhor cena por `eo:cloud_cover` e
  conferir a SCL na área do recorte, não na cena inteira.
- Offset diferente entre baselines → R3.3.

## Estratégia de testes

| Requisito | Teste |
| --- | --- |
| R3.2 | Abrir o TIFF gerado: shape (4, 512, 512), CRS, transform igual ao kit, tags presentes |
| R3.5 | `sha256sum -c` na pasta de saída |
| R3.6 | Upload pela app em produção; análise `completed` |
| R3.7 | Tabela e figura salvas em `docs/evidencias/` |
| R3.8 | `test_temporal.py` com dois rasters sintéticos |
