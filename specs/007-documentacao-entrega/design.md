---
id: "007"
titulo: Documentação, nota de pesquisa e entrega
status: rascunho
---

# 007 — Documentação e entrega: design

## Arquivos

| Arquivo | Conteúdo |
| --- | --- |
| `README.md` | Visão, link da app, execução local, arquitetura (diagrama), método, serviços e cotas, segurança, limitações, testes, estrutura |
| `docs/nota-de-pesquisa.md` | Nota de até 2 páginas (exportável para PDF) |
| `docs/uso-de-ia.md` | Diário preenchido durante o dia |
| `docs/evidencias/` | Saída de testes, prints de UI, figuras de calibração e comparação |
| `scripts/compare_mapbiomas.py` | *(P1)* Concordância com a classe café do MapBiomas |
| `.github/workflows/keepalive.yml` | Cron a cada 3 dias chamando `/health` |
| `LICENSE` | Licença do código |

## Fontes a conferir antes de citar (C5.2)

- Metodologia MapBiomas (ATBD, apêndice de agricultura/café) e mapeamento do
  parque cafeeiro da Conab.
- Moreira, Adami e Rudorff (2004), análise espectral e temporal do café em
  imagens Landsat, Pesquisa Agropecuária Brasileira.
- Documentação Sentinel-2 L2A da ESA (bandas, SCL, termos) e Rouse et al.
  (1974) para o NDVI.

## Alternativas para a nota

1. Classificador supervisionado (Random Forest) com amostras do MapBiomas:
   recusado por herdar erros e tornar a verificação circular.
2. Modelo de fundação geoespacial (Prithvi) ou SAM: recusado por peso na
   hospedagem gratuita e necessidade de ajuste fino para café.

## Roteiro do vídeo (3 min)

1. 0:00–0:20 problema e aviso "áreas potenciais, não café validado".
2. 0:20–0:50 login, upload do kit, carregamento.
3. 0:50–1:40 mapa, legenda, data, hectares, clique no polígono, downloads.
4. 1:40–2:20 chat apresentando e respondendo sobre confiança.
5. 2:20–2:50 imagem adicional e o que muda entre datas.
6. 2:50–3:00 links.

## Estratégia de verificação

| Requisito | Verificação |
| --- | --- |
| R7.1, R7.2 | Checklist das seções do README |
| R7.4–R7.7 | Nota exportada em PDF com ≤ 2 páginas |
| R7.10 | `git log -p \| grep -iE "key\|secret"`; busca por e-mails e nomes |
| R7.11, R7.12 | Execução manual em aba anônima |
