---
id: "004"
titulo: Mapa, telas e estados da interface
status: rascunho
---

# 004 — Mapa e UI: design

## Visão geral

SPA em Vite + React + TypeScript, Tailwind e shadcn/ui. Roteamento com React
Router; dados com TanStack Query (cache, retry e estados prontos).

```text
/login            Login.tsx
/                 Analyses.tsx      (lista + upload)
/analyses/:id     Analysis.tsx      (mapa + painel + chat da spec 005)
```

## Componentes e arquivos

| Arquivo | Responsabilidade |
| --- | --- |
| `frontend/src/pages/Analyses.tsx` | Lista, estado vazio, upload |
| `frontend/src/pages/Analysis.tsx` | Layout mapa + painel (grid responsivo) |
| `frontend/src/components/Upload.tsx` | Drag and drop, validação no cliente, progresso |
| `frontend/src/components/MapView.tsx` | MapLibre GL: `image` source com 4 cantos, `geojson` source, popup |
| `frontend/src/components/Legend.tsx` | Legenda e controles de camada/opacidade |
| `frontend/src/components/Summary.tsx` | Cartões de números, data, aviso, justificativa |
| `frontend/src/components/Downloads.tsx` | Botões de PNG e GeoJSON (URLs assinadas) |
| `frontend/src/components/states/` | `Loading`, `ErrorState`, `EmptyState`, `ServerWaking` |
| `frontend/src/lib/api.ts` | Chamadas tipadas; timer de 5 s para o aviso de servidor frio |

## Contratos

Consome `GET /analyses`, `GET /analyses/{id}`, `POST /analyses`,
`DELETE /analyses/{id}` (spec 002). O `POST` responde `202` com o `id` e o
processamento roda em plano de fundo: a tela da análise abre na hora e o
`useQuery` de `GET /analyses/{id}` usa `refetchInterval` de 2 s enquanto
`status = "processing"` (e `false` depois); a lista faz o mesmo se tiver
alguma análise em `processing`. O tempo decorrido sai de `created_at`. O
overlay usa `bounds_wgs84` na ordem
exigida pelo MapLibre: superior-esquerdo, superior-direito, inferior-direito,
inferior-esquerdo.

## Decisões

| Decisão | Alternativa recusada | Motivo |
| --- | --- | --- |
| MapLibre GL | Leaflet; Mapbox | Gratuito, WebGL, overlay de imagem por 4 cantos nativo; Mapbox exige token |
| shadcn/ui + Tailwind | MUI | Visual consistente sem peso de tema; componentes no próprio repo |
| PNG gerado no backend | Renderizar canvas no front | Download idêntico ao que foi processado; menos código no cliente |
| TanStack Query | `useEffect` manual | Estados de loading/erro/retry consistentes |

## Riscos

- Overlay deslocado → conferir cantos contra `area_estudo.geojson` desenhado
  como camada de limite.
- URLs assinadas expiram com a página aberta → refazer `GET /analyses/{id}`
  ao baixar.

## Estratégia de testes

| Requisito | Teste |
| --- | --- |
| R4.5, R4.6 | Manual: overlay alinhado ao limite da área; números iguais ao `GET /analyses/{id}` |
| R4.13, R4.14, R4.15 | Manual: backend parado, resposta 500 forçada, raster sem candidatos |
| R4.16 | DevTools em 375 px e 1440 px; prints em `docs/evidencias/` |
| R4.3 | Manual: `.png` e arquivo > 20 MB rejeitados no cliente |
