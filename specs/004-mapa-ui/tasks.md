---
id: "004"
titulo: Mapa, telas e estados da interface
status: aprovado
---

# 004 — Mapa e UI: tarefas

Bloco do dia: 14h às 16h30. Corte se estourar: alternância RGB/classificação e opacidade; depois o
movimento e acabamento (T4.9), que entra por último porque refina telas prontas.

- [ ] **T4.1** (P0) Roteamento, layout base, TanStack Query e componentes de estado.
  - _Req: R4.12, R4.13, R4.14, R4.17_
  - Arquivos: `frontend/src/App.tsx`, `frontend/src/components/states/`
  - Verificação: backend parado mostra aviso de servidor e erro com "tentar de novo".
- [ ] **T4.2** (P0) Lista de análises com estado vazio e link do kit.
  - _Req: R4.1, R4.2_
  - Arquivos: `frontend/src/pages/Analyses.tsx`
  - Verificação: conta nova vê o estado vazio.
- [ ] **T4.3** (P0) Upload com drag and drop, validação no cliente, progresso do envio e estado "processando" com consulta periódica.
  - _Req: R4.3, R4.4_
  - Arquivos: `frontend/src/components/Upload.tsx`, `frontend/src/pages/Analysis.tsx`
  - Verificação: `.png` e arquivo grande rejeitados; kit enviado abre a análise em "processando" e passa para o resultado sem recarregar; análise `failed` mostra a mensagem e a opção de reenviar.
- [ ] **T4.4** (P0) Mapa com overlay, polígonos, limite e popup.
  - _Req: R4.5, R4.7_
  - Arquivos: `frontend/src/components/MapView.tsx`
  - Verificação: overlay alinhado ao limite da área de estudo.
- [ ] **T4.5** (P0) Painel: legenda, data, cartões, aviso, justificativa, resultado vazio.
  - _Req: R4.6, R4.9, R4.15_
  - Arquivos: `frontend/src/components/Legend.tsx`, `frontend/src/components/Summary.tsx`
  - Verificação: números iguais ao JSON da API.
- [ ] **T4.6** (P0) Downloads e apagar análise.
  - _Req: R4.8, R4.11_
  - Arquivos: `frontend/src/components/Downloads.tsx`
  - Verificação: PNG e GeoJSON baixados abrem; GeoJSON válido no geojson.io.
- [ ] **T4.7** (P1) Alternância RGB/classificação e opacidade.
  - _Req: R4.10_
  - Verificação: manual.
- [ ] **T4.8** (P0) Revisão responsiva em 375 px e desktop.
  - _Req: R4.16_
  - Verificação: prints em `docs/evidencias/ui-375.png` e `ui-desktop.png`.
- [ ] **T4.9** (P1) Movimento e acabamento: tokens de duração e curva, entrada
  orquestrada do resultado, retorno das ações, movimento reduzido no mapa e
  revisão de detalhes visuais.
  - _Req: R4.17, R4.18, R4.19, R4.20, R4.21_
  - Arquivos: `frontend/src/index.css`, `frontend/src/lib/motion.ts`,
    `frontend/src/components/{MapView,Summary,Legend,Downloads,Upload}.tsx`,
    `frontend/src/components/states/`
  - Verificação: gravação da transição processando → resultado em
    `docs/evidencias/ui-resultado.webm`; com `prefers-reduced-motion: reduce`
    nada anima, nem o mapa; CLS < 0,1 no Performance do DevTools; nenhuma
    dependência nova no `package.json`.
