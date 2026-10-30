import { CircleAlert, CircleCheck, LoaderCircle } from 'lucide-react'
import type { AnalysisStatus } from '@/lib/api'

const LABELS: Record<AnalysisStatus, string> = {
  processing: 'Processando',
  completed: 'Concluída',
  failed: 'Falhou',
}

export function StatusBadge({ status }: { status: AnalysisStatus }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-sm whitespace-nowrap">
      {status === 'processing' && <LoaderCircle className="size-3.5 animate-spin text-canopy" aria-hidden />}
      {status === 'completed' && <CircleCheck className="size-3.5 text-canopy" aria-hidden />}
      {status === 'failed' && <CircleAlert className="size-3.5 text-muted-foreground" aria-hidden />}
      {LABELS[status]}
    </span>
  )
}
