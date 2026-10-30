import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
import { ErrorState } from '@/components/states/ErrorState'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ApiError, getAnalysis } from '@/lib/api'
import { analysisKey } from '@/lib/query'

export function Analysis() {
  const { id = '' } = useParams()
  const analysis = useQuery({ queryKey: analysisKey(id), queryFn: () => getAnalysis(id) })

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

  return (
    <main className="flex-1 p-4 sm:p-6">
      <p className="font-mono text-sm">{analysis.data.filename}</p>
    </main>
  )
}
