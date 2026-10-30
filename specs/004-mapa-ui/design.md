---
id: "004"
titulo: Mapa, telas e estados da interface
status: concluido
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
| `frontend/src/lib/format.ts` | Hectares, porcentagem e datas em pt-BR |

Segunda data: o `Upload` tem uma seção recolhida com `image_2` e `scl_2`; o
`Summary` mostra a data da segunda imagem quando `stats.second_acquired_at`
existe.

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
| OpenFreeMap Positron | CARTO; Esri World Imagery; OSM raster | Sem chave nem limite; tons neutros não competem com o overlay e o vermelho cereja; CARTO pede chave, Esri pede conta ArcGIS |
| Upload por `XMLHttpRequest` | `fetch` | `fetch` não informa progresso do envio (R4.4) |
| Download por `fetch` + blob | `<a download>` na URL assinada | `download` é ignorado entre origens; o blob garante o nome do arquivo |
| CSS + `tw-animate-css` + transições do MapLibre | `framer-motion` / `motion` | Cobre o que a UI precisa sem dependência nova (regra de cadeia de suprimentos) |
| Número final direto | Contagem animada de hectares | Valores intermediários não vêm do processamento (C2) |
| Barra indeterminada | Barra com porcentagem | O backend não mede progresso; porcentagem seria inventada |

## Movimento e acabamento (R4.17 a R4.21)

A direção é a de um instrumento de medição, não de uma landing page: o
movimento explica o que mudou e some. Nada de mola, quique, parallax ou
animação em loop fora do estado de processamento.

**Tokens** (em `index.css`, usados por Tailwind e pelo MapLibre):

| Token | Valor | Uso |
| --- | --- | --- |
| `--duration-fast` | 120 ms | hover, pressionar, foco, tooltip |
| `--duration-base` | 200 ms | popup, diálogo, troca de tela |
| `--duration-slow` | 320 ms | overlay e polígonos entrando no mapa |
| `--ease-out` | `cubic-bezier(0.2, 0, 0, 1)` | tudo que entra |
| `--ease-in` | `cubic-bezier(0.4, 0, 1, 1)` | tudo que sai (saída ~30% mais curta) |

Só `opacity` e `transform` animam no DOM, para não custar layout.

**Momento principal: o resultado chegando (R4.19).** É o único momento
orquestrado da aplicação. Quando o polling vê `completed`:

1. `fitBounds` nos `bounds_wgs84` com `duration` de 800 ms;
2. o overlay vai de `raster-opacity` 0 até a opacidade escolhida (320 ms);
3. os polígonos entram por `fill-opacity` e depois o contorno (320 ms, com
   120 ms de atraso);
4. os cartões do painel entram em cascata, com 40 ms entre um e outro
   (`animate-in fade-in slide-in-from-bottom-1`, do `tw-animate-css` que já
   está no projeto).

Os números aparecem já com o valor final: a contagem de 0 até 214,54 ha foi
recusada porque mostraria valores que o processamento não produziu (C2) e
poderia ser capturada num print.

**Processamento.** Barra indeterminada fina no topo do painel e o tempo
decorrido em `tabular-nums`; sem porcentagem, porque o backend não informa
progresso. Mudança de status anunciada por `aria-live="polite"`.

**Retorno das ações.**

- Botões: estado de pressionado (`active:translate-y-px`), desabilitado com
  spinner durante a chamada, e o rótulo segue o verbo da ação ("Baixar PNG" →
  "Baixando…" → volta ao rótulo).
- Polígono: realce no hover via `feature-state` (contorno mais grosso) e
  cursor de ponteiro; popup com fade de 120 ms.
- Apagar: diálogo de confirmação do `radix-ui` (já instalado) com fade e zoom
  de 200 ms. A exclusão acontece na tela da análise; ao voltar, a lista já
  abre sem o item (cache atualizado na hora, sem esperar a nova consulta).
- Upload: zona de soltar muda de tracejada para contínua em `--canopy` ao
  arrastar por cima; arquivo recusado mostra o motivo na própria zona.

**Acabamento.**

- O vermelho cereja (`--cherry`) marca só área potencial e erro destrutivo;
  não é usado em hover, foco ou decoração, para não diluir o significado.
- Números com `tabular-nums` e formato pt-BR; unidade (`ha`, `%`) em
  `font-mono` menor que o valor.
- Profundidade com borda de 1 px; sombra só nos controles que flutuam sobre o
  mapa.
- Ícones `lucide-react` com o mesmo `strokeWidth` em todo o app.
- Skeletons com a mesma geometria do conteúdo final, para não pular o layout.
- `document.title` por tela ("Análise · arquivo.tif · Global Watch").
- O estado vazio reaproveita a `NdviRuler` da tela de login como ilustração
  do método, em vez de uma imagem genérica.

O voo do `fitBounds` só acontece quando a tela viu a análise em `processing`
(R4.19); abrir uma análise já concluída enquadra direto e mantém só os fades
do overlay, dos polígonos e do painel. Os fades do mapa esperam a imagem e o
GeoJSON carregarem: sem isso a transição acabaria antes de haver o que mostrar.

**Movimento reduzido (R4.20).** A regra global de `index.css` cobre CSS, mas
não o MapLibre. `lib/motion.ts` expõe `prefersReducedMotion()` (lido de
`matchMedia` e atualizado no `change`); com ele, `fitBounds` usa
`duration: 0` e as transições de pintura do mapa ficam em 0.

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
| R4.18, R4.19 | Manual: gravação curta da transição processando → resultado em `docs/evidencias/ui-resultado.webm` |
| R4.20 | DevTools → Rendering → `prefers-reduced-motion: reduce`: mapa enquadra sem voo, nada anima |
| R4.21 | Painel Performance do DevTools: CLS < 0,1 ao carregar a análise; nenhum valor diferente do JSON aparece durante a entrada |
