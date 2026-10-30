import { useQuery } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { Link } from 'react-router'
import { NdviRuler } from '@/components/NdviRuler'
import { StatusBadge } from '@/components/StatusBadge'
import { EmptyState } from '@/components/states/EmptyState'
import { ErrorState } from '@/components/states/ErrorState'
import { Skeleton } from '@/components/ui/skeleton'
import { type AnalysisListItem, listAnalyses } from '@/lib/api'
import { formatDateTime, formatHa, formatImageDate } from '@/lib/format'
import { KIT_IMAGE_URL, KIT_SCL_URL } from '@/lib/kit'
import { analysesKey } from '@/lib/query'

// Colunas da lista no desktop; no celular cada análise vira um bloco de duas linhas.
const COLUMNS = 'sm:grid sm:grid-cols-[minmax(0,1fr)_9.5rem_9rem_7.5rem_7.5rem] sm:items-center sm:gap-4'

export function Analyses() {
  const analyses = useQuery({
    queryKey: analysesKey,
    queryFn: listAnalyses,
    // Consulta a cada 2 s só enquanto houver análise processando (R4.4).
    refetchInterval: (query) =>
      query.state.data?.some((item) => item.status === 'processing') ? 2000 : false,
  })

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-8">
      <h1 className="font-heading text-4xl font-[640] tracking-tight [font-stretch:75%]">
        Suas análises
      </h1>

      <section className="mt-8" aria-label="Análises enviadas" aria-busy={analyses.isPending}>
        {analyses.isPending && <ListSkeleton />}
        {analyses.isError && (
          <ErrorState
            error={analyses.error}
            onRetry={() => analyses.refetch()}
            retrying={analyses.isFetching}
          />
        )}
        {analyses.isSuccess && analyses.data.length === 0 && <NoAnalyses />}
        {analyses.isSuccess && analyses.data.length > 0 && <AnalysisList items={analyses.data} />}
      </section>
    </main>
  )
}

function AnalysisList({ items }: { items: AnalysisListItem[] }) {
  return (
    <div className="overflow-hidden rounded-lg border border-border bg-card">
      <div className={`hidden border-b border-border px-4 py-2 font-mono text-[11px] tracking-wide text-muted-foreground uppercase ${COLUMNS}`}>
        <span>Arquivo</span>
        <span>Enviada em</span>
        <span>Data da imagem</span>
        <span>Status</span>
        <span className="text-right">Área potencial</span>
      </div>
      <ul className="divide-y divide-border">
        {items.map((item) => (
          <li key={item.id}>
            <Link
              to={`/analyses/${item.id}`}
              className={`block px-4 py-3 transition-colors outline-none hover:bg-muted/60 focus-visible:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:ring-inset ${COLUMNS}`}
            >
              <span className="flex min-w-0 items-baseline justify-between gap-3">
                <span className="min-w-0 truncate font-medium" title={item.filename}>
                  {item.filename}
                </span>
                <span className="shrink-0 sm:hidden">
                  <StatusBadge status={item.status} />
                </span>
              </span>
              <span className="mt-1 flex flex-wrap gap-x-3 text-sm text-muted-foreground sm:contents">
                <span className="whitespace-nowrap tabular-nums">
                  <span className="sm:hidden">Enviada </span>
                  {formatDateTime(item.created_at)}
                </span>
                {item.acquired_at ? (
                  <span className="whitespace-nowrap">
                    <span className="sm:hidden">Imagem de </span>
                    {formatImageDate(item.acquired_at)}
                  </span>
                ) : (
                  <span className="hidden sm:inline">—</span>
                )}
              </span>
              <span className="hidden sm:block">
                <StatusBadge status={item.status} />
              </span>
              <PotentialArea value={item.potential_area_ha} />
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}

function PotentialArea({ value }: { value: number | null }) {
  if (value === null) return <span className="hidden text-right text-muted-foreground sm:block">—</span>
  return (
    <span className="mt-1 flex items-baseline gap-1.5 tabular-nums sm:mt-0 sm:justify-end">
      <span className="size-2 self-center rounded-[2px] bg-cherry" aria-hidden />
      <span className="sm:hidden text-sm text-muted-foreground">Área potencial</span>
      <span className="font-medium">{formatHa(value)}</span>
      <span className="font-mono text-xs text-muted-foreground">ha</span>
    </span>
  )
}

function NoAnalyses() {
  return (
    <EmptyState
      title="Envie uma imagem Sentinel-2 para começar"
      illustration={
        <div className="mb-8 max-w-3xl">
          <NdviRuler />
        </div>
      }
    >
      <p>
        GeoTIFF com as bandas azul, verde, vermelho e infravermelho próximo (B02, B03, B04, B08),
        de preferência com a camada de qualidade SCL. Sem imagem à mão? Use o recorte de exemplo,
        de Guaxupé (MG) em agosto de 2025.
      </p>
      <p className="mt-4 flex flex-wrap gap-x-5 gap-y-2">
        <a className="inline-flex items-center gap-1.5 font-medium text-foreground underline-offset-4 hover:underline" href={KIT_IMAGE_URL}>
          <Download className="size-4" aria-hidden />
          Imagem de exemplo (1,4 MB)
        </a>
        <a className="inline-flex items-center gap-1.5 font-medium text-foreground underline-offset-4 hover:underline" href={KIT_SCL_URL}>
          <Download className="size-4" aria-hidden />
          SCL de exemplo (7 KB)
        </a>
      </p>
    </EmptyState>
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
