import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { Link, useParams } from 'react-router'
import { ErrorState } from '@/components/states/ErrorState'
import { Processing } from '@/components/states/Processing'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ApiError, getAnalysis } from '@/lib/api'
import { analysesKey, analysisKey } from '@/lib/query'

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

  return (
    <main className="flex-1 p-4 sm:p-6">
      <p className="font-mono text-sm">{data.filename}</p>
    </main>
  )
}
