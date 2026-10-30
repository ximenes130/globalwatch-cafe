---
id: "004"
titulo: Mapa, telas e estados da interface
status: rascunho
desafio: [4, 6]
pontos: UI/UX e responsividade (20)
prioridade: P0
---

# 004 — Mapa e UI: requisitos

## Objetivo

Uma interface bonita, consistente e responsiva que mostra a imagem e as áreas
potenciais no mapa, com números claros, downloads e estados explícitos de
carregamento, erro e ausência de resultado.

## Histórias

- **H4.1** Como usuário, quero ver minhas análises e começar uma nova
  facilmente, para não me perder no fluxo.
- **H4.2** Como usuário, quero ver a imagem e os polígonos sobre um mapa com
  legenda, data e hectares, para entender o resultado.
- **H4.3** Como usuário, quero baixar a imagem com os polígonos e o GeoJSON,
  para usar o resultado em outra ferramenta.
- **H4.4** Como usuário de celular, quero usar o app numa tela pequena, para
  consultar resultados em campo.

## Critérios de aceite (EARS)

### Lista e upload

- **R4.1** — O SISTEMA DEVE listar as análises do usuário com nome do arquivo,
  data de criação, data da imagem, status e área potencial.
- **R4.2** — ENQUANTO o usuário não tiver análises, O SISTEMA DEVE mostrar um
  estado vazio útil ("Envie uma imagem Sentinel-2 para começar") com link para
  baixar a imagem de exemplo do kit.
- **R4.3** — O upload DEVE aceitar arrastar e soltar ou seleção de arquivo,
  validar no cliente extensão `.tif/.tiff` e tamanho (≤ 20 MB) e aceitar a SCL
  opcional.
- **R4.4** — ENQUANTO o upload e o processamento ocorrem, O SISTEMA DEVE
  mostrar progresso e bloquear o reenvio.

### Tela da análise

- **R4.5** — O SISTEMA DEVE mostrar um mapa com basemap gratuito, a imagem
  sobreposta pelos 4 cantos em WGS84 e os polígonos em GeoJSON.
- **R4.6** — O SISTEMA DEVE mostrar legenda (área potencial de café, área
  mascarada, limite da imagem), a data da imagem e cartões com área total,
  área potencial (ha e %), e número de polígonos.
- **R4.7** — QUANDO o usuário clicar em um polígono, O SISTEMA DEVE mostrar
  `id`, `area_ha` e `ndvi_mean` do polígono.
- **R4.8** — O SISTEMA DEVE oferecer download do PNG com polígonos e do
  GeoJSON.
- **R4.9** — O SISTEMA DEVE exibir de forma visível o aviso de que o resultado
  é potencial e não validado, e a justificativa técnica da classificação.
- **R4.10** *(P1)* — O SISTEMA DEVE permitir alternar o overlay entre RGB e
  classificação e ajustar a opacidade.
- **R4.11** — O usuário DEVE poder apagar uma análise, com confirmação.

### Estados

- **R4.12** — ENQUANTO dados carregam, O SISTEMA DEVE mostrar skeletons.
- **R4.13** — SE o backend demorar mais de 5 s para responder (servidor
  dormindo), ENTÃO O SISTEMA DEVE avisar "acordando o servidor, pode levar até
  um minuto".
- **R4.14** — SE ocorrer erro, ENTÃO O SISTEMA DEVE mostrar mensagem
  compreensível e uma ação de tentar de novo; 429 mostra o limite diário.
- **R4.15** — QUANDO a análise tiver zero polígonos, O SISTEMA DEVE mostrar
  "nenhuma área potencial encontrada" com a explicação dos critérios.

### Responsividade e consistência

- **R4.16** — O layout DEVE funcionar a partir de 375 px de largura sem
  rolagem horizontal: no celular, mapa em cima e painel embaixo; no desktop,
  mapa à esquerda e painel à direita.
- **R4.17** — A interface DEVE usar um único sistema de componentes, cores e
  tipografia, com foco visível e contraste adequado.

## Fora de escopo

- Edição de polígonos no mapa.
- Tema escuro (só se sobrar tempo).

## Questões abertas

- Basemap: OSM raster ou Esri World Imagery (satélite ajuda a inspecionar,
  conferir termos de uso).
