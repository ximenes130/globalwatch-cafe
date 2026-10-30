import { useQuery, useQueryClient } from '@tanstack/react-query'
import { lazy, Suspense, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import { Legend } from '@/components/Legend'
import { ErrorState } from '@/components/states/ErrorState'
import { Processing } from '@/components/states/Processing'
import { Summary } from '@/components/Summary'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import type { Overlay } from '@/components/MapView'
import { type Analysis as AnalysisData, ApiError, getAnalysis } from '@/lib/api'
import { analysesKey, analysisKey } from '@/lib/query'

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

  // Quando o processamento termina, a lista precisa refletir o novo status.
  useEffect(() => {
    if (status && status !== 'processing') queryClient.invalidateQueries({ queryKey: analysesKey, exact: true })
  }, [status, queryClient])

  if (analysis.isPending) {
    return (
      <main className="flex-1 p-4 sm:p-6" aria-busy>
        <Skeleton className="h-[50vh] w-full" />
      </main>
    )
  }

  if (analysis.isError) {
    const notFound = analysis.error instanceof ApiError && analysis.error.status === 404
    return (
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-8">
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
      <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-10 sm:px-8">
        <Processing filename={data.filename} createdAt={data.created_at} />
      </main>
    )
  }

  if (data.status === 'failed') {
    return (
      <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-10 sm:px-8">
        <ErrorState
          error={new Error(data.error ?? 'O processamento falhou.')}
          title={`Não foi possível analisar ${data.filename}`}
        >
          <Button asChild>
            <Link to="/">Enviar outra imagem</Link>
          </Button>
        </ErrorState>
      </main>
    )
  }

  return <Result analysis={data} />
}

function Result({ analysis }: { analysis: AnalysisData }) {
  const [overlay] = useState<Overlay>('rgb')
  const [opacity] = useState(1)
  const { bounds_wgs84: corners, urls } = analysis

  return (
    // No desktop o mapa ocupa a altura que sobra abaixo do cabeçalho (57 px) e o painel rola.
    // `flex-none` e linha `minmax(0, 1fr)`: sem eles, o painel comprido estica o main e o mapa.
    <main className="flex flex-1 flex-col lg:grid lg:h-[calc(100dvh-57px)] lg:flex-none lg:grid-cols-[minmax(0,1fr)_26rem] lg:grid-rows-[minmax(0,1fr)]">
      <div className="relative h-[60svh] border-b border-border lg:h-full lg:border-r lg:border-b-0">
        {corners && urls ? (
          <Suspense fallback={<Skeleton className="size-full rounded-none" />}>
            <MapView key={analysis.id} corners={corners} urls={urls} overlay={overlay} opacity={opacity} />
          </Suspense>
        ) : (
          <div className="grid size-full place-items-center p-6 text-sm text-muted-foreground">
            Mapa indisponível: a análise não tem limites gravados.
          </div>
        )}
      </div>
      <aside className="p-4 sm:p-6 lg:overflow-y-auto" aria-label="Resultado da análise">
        {analysis.stats && analysis.rationale ? (
          <Summary
            analysis={analysis}
            stats={analysis.stats}
            rationale={analysis.rationale}
            legend={<Legend stats={analysis.stats} />}
          />
        ) : (
          <p className="text-sm text-muted-foreground">A análise não tem estatísticas gravadas.</p>
        )}
      </aside>
    </main>
  )
}
