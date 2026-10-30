import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { ErrorState } from '@/components/states/ErrorState'
import { Skeleton } from '@/components/ui/skeleton'
import { listAnalyses } from '@/lib/api'
import { analysesKey } from '@/lib/query'

export function Analyses() {
  const analyses = useQuery({ queryKey: analysesKey, queryFn: listAnalyses })

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-8">
      <h1 className="font-heading text-4xl font-[640] tracking-tight [font-stretch:75%]">
        Suas análises
      </h1>

      <section className="mt-8" aria-live="polite" aria-busy={analyses.isPending}>
        {analyses.isPending && <ListSkeleton />}
        {analyses.isError && (
          <ErrorState
            error={analyses.error}
            onRetry={() => analyses.refetch()}
            retrying={analyses.isFetching}
          />
        )}
        {analyses.isSuccess && (
          <ul>
            {analyses.data.map((item) => (
              <li key={item.id}>
                <Link to={`/analyses/${item.id}`}>{item.filename}</Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  )
}

function ListSkeleton() {
  return (
    <div className="divide-y divide-border rounded-lg border border-border bg-card" aria-label="Carregando análises">
      {[0, 1, 2].map((row) => (
        <div key={row} className="flex items-center gap-4 px-4 py-4">
          <Skeleton className="h-4 w-48" />
          <Skeleton className="ml-auto h-4 w-20" />
        </div>
      ))}
    </div>
  )
}
