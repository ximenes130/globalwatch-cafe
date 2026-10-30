---
id: "007"
titulo: Documentação, nota de pesquisa e entrega
status: aprovado
---

# 007 — Documentação e entrega: design

## Arquivos

| Arquivo | Conteúdo |
| --- | --- |
| `README.md` | Link da app, o que é, execução local, arquitetura (diagrama Mermaid), método, serviços e cotas, limites e retenção, segurança, limitações, testes e evidências, estrutura, licença e atribuição |
| `docs/nota-de-pesquisa.md` | Nota de até 2 páginas, com as quatro seções pedidas no enunciado |
| `docs/nota-de-pesquisa.pdf` | Exportação da nota, para conferir as 2 páginas |
| `docs/metodo.md` | O que sai da nota hoje: tabelas de calibração, comparação com o MapBiomas e as duas datas, com as figuras |
| `docs/uso-de-ia.md` | Diário preenchido durante o dia, com ferramentas e casos de erro |
| `scripts/inspect_points.py` | Sorteia os pontos da inspeção visual e monta a prancha |
| `docs/evidencias/inspecao/` | Prancha com os recortes e `inspecao-visual.md` com a tabela |
| `LICENSE` | MIT |

## Nota em duas páginas

A nota atual tem cerca de 260 linhas, perto de cinco páginas. Ela fica com o
essencial de cada seção e números de resumo:

1. Problema e abordagem: a cascata em cinco linhas.
2. Fontes: uma ou duas linhas por fonte, dizendo o que foi usado dela.
3. Alternativas: Random Forest com amostras do MapBiomas e o modelo Coffee
   Probability 2026a. Cada uma com o motivo da recusa em uma frase.
4. Dados e modelos: tabela curta com origem, licença e atribuição.
5. Verificação, erro e limitações. Verificação: sanidade de área, inspeção
   visual e concordância com o MapBiomas. Erro: o teto do NDVI de 0,78 para
   0,72, com antes e depois. Limitações em tópicos.

Tabelas e percentuais por classe vão para `docs/metodo.md`. A exportação usa
`pandoc` para HTML e o Chrome headless para PDF A4. A conferência das páginas
é feita com `pdfinfo`.

## Inspeção visual (R7.7)

`scripts/inspect_points.py` roda o mesmo pipeline do app sobre o kit e sorteia
15 pontos com semente fixa:

- 10 dentro da área potencial;
- 3 excluídos por NDVI alto (dossel denso);
- 2 excluídos por NDVI baixo.

Para cada ponto, a prancha mostra um recorte RGB de 600 x 600 m com a área
potencial contornada. A tabela registra o que se vê: talhão com linhas, mata,
pasto, solo, área urbana ou indefinido. A primeira leitura é da IA, com visão;
o usuário revisa e corrige. O resultado é descrito em contagens, sem
percentual, porque 15 pontos não estimam acurácia.

## Dados e modelos (R7.6)

| Item | Origem | Condição de uso |
| --- | --- | --- |
| Kit e cena adicional | Sentinel-2 L2A via Earth Search (Element 84) | Sentinel Data Legal Notice; "Contains modified Copernicus Sentinel data" |
| MapBiomas Coleção 10 | Plataforma MapBiomas | Licença conferida no site oficial antes de citar |
| LLM | Claude Haiku 5.5 (`claude-haiku-5-5`), API da Anthropic | Termos comerciais da API; não treina com os dados enviados pela API |
| Basemap | OpenFreeMap (estilo Positron) sobre OpenStreetMap | Dados ODbL, com atribuição "© OpenStreetMap contributors" no mapa |
| Coffee Probability 2026a | Forest Data Partnership | Considerado e não usado; CC BY 4.0 |

Cada condição é conferida na fonte durante a T7.2, com a data da consulta.

## Fontes já citadas e conferidas

Parreiras et al. (2025), Maskell et al. (2021), Souza et al. (2019),
Gitelson, Kaufman e Merzlyak (1996) e McFeeters (1996), com DOI. Rouse et al.
(1974) e a documentação L2A da ESA só entram se forem abertas e conferidas.

## README: cotas e suspensão (R7.2, R7.3)

| Serviço | O que documentar |
| --- | --- |
| Render free | Hiberna após 15 min sem tráfego, partida a frio de até ~1 min, horas mensais de instância |
| Supabase free | Pausa após 7 dias sem atividade, limites de banco, Storage e usuários |
| Anthropic | Pago por uso, com teto de gasto (T6.6); o avaliador não precisa de chave |
| GitHub Actions | Minutos grátis em repositório público; agendados desligam após 60 dias sem atividade |
| Limites da app | 20 envios e 50 mensagens por usuário por dia, retenção de 7 dias |

Os números são conferidos nas páginas de preço de cada serviço, com a data da
consulta.

## Roteiro do vídeo (3 min)

1. 0:00–0:15: problema e aviso "áreas potenciais, não café validado".
2. 0:15–0:40: login com Google, upload do kit, estado de processamento.
3. 0:40–1:30: mapa, legenda, data, hectares, clique no polígono, justificativa
   e downloads.
4. 1:30–2:10: chat apresentando a análise e respondendo sobre confiança e
   limitações.
5. 2:10–2:45: imagem adicional de janeiro e o kit com a segunda data, e o que
   muda.
6. 2:45–3:00: limites do dia, retenção, links do repositório e da app.

## Estratégia de verificação

| Requisito | Verificação |
| --- | --- |
| R7.1–R7.3 | Checklist das seções do README; Mermaid renderizado no GitHub |
| R7.4–R7.8, R7.13 | `pdfinfo` mostra ≤ 2 páginas; cada referência aberta |
| R7.7 | Prancha e tabela da inspeção revisadas pelo usuário |
| R7.9 | Diário com ferramentas, validação e casos de erro |
| R7.10 | Greps de segredos e dados pessoais no histórico inteiro; `LICENSE` presente |
| R7.11, R7.12 | Execução manual em aba anônima e vídeo, pelo usuário |
