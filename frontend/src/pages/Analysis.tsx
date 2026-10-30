import { useQuery, useQueryClient } from '@tanstack/react-query'
import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router'
import { Tabs } from 'radix-ui'
import { Chat } from '@/components/Chat'
import { DeleteAnalysis } from '@/components/DeleteAnalysis'
import { Downloads } from '@/components/Downloads'
import { Legend } from '@/components/Legend'
import { ErrorState } from '@/components/states/ErrorState'
import { Processing } from '@/components/states/Processing'
import { Summary } from '@/components/Summary'
import { DeletionNote } from '@/components/UsageNote'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import type { Focus, Overlay } from '@/components/MapView'
import { type Analysis as AnalysisData, ApiError, getAnalysis } from '@/lib/api'
import { analysesKey, analysisKey } from '@/lib/query'
import { useDocumentTitle } from '@/lib/use-document-title'

// MapLibre pesa ~1 MB: só carrega quando uma análise concluída abre.
const MapView = lazy(() => import('@/components/MapView'))

export function Analysis() {
  const { id = '' } = useParams()
  const queryClient = useQueryClient()
  const analysis = useQuery({
    queryKey: analysisKey(id),
    queryFn: () => getAnalysis(id),
    // Consulta a cada 2 s enquanto processa; para em `completed` ou `failed` (R4.4).
    refetchInterval: (query) => (query.state.data?.status === 'processing' ? 2000 : false),
  })
  const status = analysis.data?.status
  useDocumentTitle(analysis.data?.filename ?? 'Análise')

  // Só quem acompanhou o processamento vê o voo até a imagem (R4.19). Atualizado no
  // render, como manda o React para estado derivado de renders anteriores.
  const [sawProcessing, setSawProcessing] = useState(false)
  if (status === 'processing' && !sawProcessing) setSawProcessing(true)

  // Quando o processamento termina, a lista precisa refletir o novo status.
  useEffect(() => {
    if (status && status !== 'processing') queryClient.invalidateQueries({ queryKey: analysesKey, exact: true })
  }, [status, queryClient])

  if (analysis.isPending) {
    return <ResultSkeleton />
  }

  if (analysis.isError) {
    const notFound = analysis.error instanceof ApiError && analysis.error.status === 404
    return (
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 duration-(--duration-base) animate-in fade-in sm:px-8">
        <ErrorState
          error={analysis.error}
          title={notFound ? 'Análise não encontrada' : undefined}
          message={notFound ? 'Ela pode ter sido apagada ou pertencer a outra conta.' : undefined}
          onRetry={notFound ? undefined : () => analysis.refetch()}
          retrying={analysis.isFetching}
        >
          <Button asChild variant="ghost">
            <Link to="/">Ver suas análises</Link>
          </Button>
        </ErrorState>
      </main>
    )
  }

  const data = analysis.data

  if (data.status === 'processing') {
    return (
      <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-10 duration-(--duration-base) animate-in fade-in sm:px-8">
        <Processing filename={data.filename} createdAt={data.created_at} />
      </main>
    )
  }

  if (data.status === 'failed') {
    return (
      <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-10 duration-(--duration-base) animate-in fade-in sm:px-8">
        <ErrorState
          error={new Error(data.error ?? 'O processamento falhou.')}
          title={`Não foi possível analisar ${data.filename}`}
        >
          <Button asChild>
            <Link to="/">Enviar outra imagem</Link>
          </Button>
          <DeleteAnalysis id={data.id} filename={data.filename} />
        </ErrorState>
      </main>
    )
  }

  return <Result analysis={data} intro={sawProcessing} />
}

// Se o mapa não carregar (basemap fora do ar), o painel aparece mesmo assim.
const REVEAL_FALLBACK_MS = 4000

type PanelTab = 'result' | 'chat'
const PANEL_TABS: [PanelTab, string][] = [
  ['result', 'Resultado'],
  ['chat', 'Assistente'],
]

function Result({ analysis, intro }: { analysis: AnalysisData; intro: boolean }) {
  const [tab, setTab] = useState<PanelTab>('result')
  // O chat só monta (e pede a apresentação) na primeira vez que a aba abre.
  const [chatOpened, setChatOpened] = useState(false)
  const openTab = (value: PanelTab) => {
    setTab(value)
    if (value === 'chat') setChatOpened(true)
  }
  const [overlay, setOverlay] = useState<Overlay>('rgb')
  const [opacity, setOpacity] = useState(1)
  const [focus, setFocus] = useState<Focus | null>(null)
  const mapBox = useRef<HTMLDivElement>(null)
  const showPolygon = (id: number, centroid: [number, number]) => {
    setFocus({ id, centroid, seq: (focus?.seq ?? 0) + 1 })
    // No celular o mapa fica acima do chat: sobe até ele.
    if (window.matchMedia('(max-width: 1023px)').matches) mapBox.current?.scrollIntoView({ block: 'start' })
  }
  const { bounds_wgs84: corners, urls } = analysis
  const hasMap = Boolean(corners && urls)
  // O painel entra depois do mapa (R4.19); sem mapa, entra direto.
  const [revealed, setRevealed] = useState(!hasMap)

  useEffect(() => {
    const timer = setTimeout(() => setRevealed(true), REVEAL_FALLBACK_MS)
    return () => clearTimeout(timer)
  }, [])

  return (
    // No desktop o mapa ocupa a altura que sobra abaixo do cabeçalho (57 px) e o painel rola.
    // `flex-none` e linha `minmax(0, 1fr)`: sem eles, o painel comprido estica o main e o mapa.
    <main className="flex flex-1 flex-col lg:grid lg:h-[calc(100dvh-57px)] lg:flex-none lg:grid-cols-[minmax(0,1fr)_26rem] lg:grid-rows-[minmax(0,1fr)]">
      <div ref={mapBox} className="relative h-[60svh] scroll-mt-2 border-b border-border lg:h-full lg:border-r lg:border-b-0">
        {corners && urls ? (
          <Suspense fallback={<Skeleton className="size-full rounded-none" />}>
            <MapView
              key={analysis.id}
              corners={corners}
              urls={urls}
              overlay={overlay}
              opacity={opacity}
              intro={intro}
              onRevealed={() => setRevealed(true)}
              focus={focus}
            />
          </Suspense>
        ) : (
          <div className="grid size-full place-items-center p-6 text-sm text-muted-foreground">
            Mapa indisponível: a análise não tem limites gravados.
          </div>
        )}
      </div>
      <aside className="lg:overflow-y-auto" aria-label="Painel da análise">
        <Tabs.Root value={tab} onValueChange={(value) => openTab(value as PanelTab)}>
          <Tabs.List
            aria-label="Conteúdo do painel"
            className="z-10 flex gap-5 border-b border-border bg-background px-4 sm:px-6 lg:sticky lg:top-0"
          >
            {PANEL_TABS.map(([value, label]) => (
              <Tabs.Trigger
                key={value}
                value={value}
                className="-mb-px border-b-2 border-transparent py-3 text-sm text-muted-foreground transition-colors duration-(--duration-fast) outline-none hover:text-foreground focus-visible:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 data-[state=active]:border-foreground data-[state=active]:font-medium data-[state=active]:text-foreground"
              >
                {label}
              </Tabs.Trigger>
            ))}
          </Tabs.List>
          {/* `forceMount`: trocar de aba não perde a conversa nem uma resposta a caminho. */}
          <Tabs.Content value="result" forceMount className="p-4 outline-none data-[state=inactive]:hidden sm:p-6">
            {analysis.stats && analysis.rationale ? (
              <Summary
                revealed={revealed}
                analysis={analysis}
                stats={analysis.stats}
                rationale={analysis.rationale}
                legend={
                  <Legend
                    stats={analysis.stats}
                    overlay={overlay}
                    onOverlayChange={setOverlay}
                    opacity={opacity}
                    onOpacityChange={setOpacity}
                  />
                }
                actions={<Downloads id={analysis.id} filename={analysis.filename} />}
                footer={
                  <div className="space-y-2">
                    <DeletionNote createdAt={analysis.created_at} />
                    <DeleteAnalysis id={analysis.id} filename={analysis.filename} />
                  </div>
                }
              />
            ) : (
              <p className="text-sm text-muted-foreground">A análise não tem estatísticas gravadas.</p>
            )}
          </Tabs.Content>
          <Tabs.Content value="chat" forceMount className="outline-none data-[state=inactive]:hidden lg:h-[calc(100%-45px)]">
            {chatOpened && (
              <Chat
                analysisId={analysis.id}
                hasSecondDate={Boolean(analysis.stats?.second_acquired_at)}
                onShowPolygon={showPolygon}
              />
            )}
          </Tabs.Content>
        </Tabs.Root>
      </aside>
    </main>
  )
}

/** Mesma geometria do resultado: mapa e painel, para a tela não pular quando os dados chegam. */
function ResultSkeleton() {
  return (
    <main
      aria-busy
      aria-label="Carregando a análise"
      className="flex flex-1 flex-col lg:grid lg:h-[calc(100dvh-57px)] lg:flex-none lg:grid-cols-[minmax(0,1fr)_26rem] lg:grid-rows-[minmax(0,1fr)]"
    >
      <Skeleton className="h-[60svh] rounded-none lg:h-full" />
      <div className="space-y-4 p-4 sm:p-6">
        <Skeleton className="h-3 w-40" />
        <Skeleton className="h-11 w-44" />
        <Skeleton className="h-2 w-full" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-20 w-full" />
      </div>
    </main>
  )
}
