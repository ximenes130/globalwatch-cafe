import { Clock } from 'lucide-react'
import { deletionDays, deletionLabel, formatResetTime, type QuotaKind, useQuota, useUsage } from '@/lib/usage'

const WORDS: Record<QuotaKind, { one: string; many: string; used: string }> = {
  uploads: { one: 'envio restante', many: 'envios restantes', used: 'os {n} envios' },
  messages: { one: 'mensagem restante', many: 'mensagens restantes', used: 'as {n} mensagens' },
}

// A partir daqui o aviso ganha destaque (cor de terra, não o vermelho da área potencial).
const WARN_AT: Record<QuotaKind, number> = { uploads: 1, messages: 5 }

/** "3 envios restantes hoje, de 5 · renova às 21:00", ou o aviso de cota esgotada (R6.16, R6.17). */
export function UsageNote({ kind, className = '' }: { kind: QuotaKind; className?: string }) {
  const quota = useQuota(kind)
  if (!quota) return null
  const words = WORDS[kind]
  const resets = formatResetTime(quota.resetsAt)

  if (quota.blocked) {
    return (
      <p role="status" className={`flex items-center gap-1.5 text-sm text-soil ${className}`}>
        <Clock className="size-3.5 shrink-0" aria-hidden />
        Você usou {words.used.replace('{n}', String(quota.limit))} de hoje. Libera às {resets}.
      </p>
    )
  }
  const warn = quota.remaining <= WARN_AT[kind]
  return (
    <p className={`text-xs ${warn ? 'font-medium text-soil' : 'text-muted-foreground'} ${className}`}>
      <span className="font-mono tabular-nums">{quota.remaining}</span>{' '}
      {quota.remaining === 1 ? words.one : words.many} hoje, de {quota.limit} · renova às {resets}
    </p>
  )
}

/** "As análises ficam guardadas por 7 dias." com o número da API (R6.18). */
export function RetentionNote({ className = '' }: { className?: string }) {
  const { data } = useUsage()
  if (!data) return null
  return (
    <p className={`text-xs text-muted-foreground ${className}`}>
      As análises ficam guardadas por {data.retention_days} dias e depois são apagadas.
    </p>
  )
}

/** Prazo de exclusão de uma análise (R6.18); `soon` mostra só quando faltam 2 dias ou menos. */
export function DeletionNote({ createdAt, soon = false, className = '' }: { createdAt: string; soon?: boolean; className?: string }) {
  const { data } = useUsage()
  if (!data) return null
  const days = deletionDays(createdAt, data.retention_days)
  if (soon && days > 2) return null
  return <p className={`text-xs ${days <= 2 ? 'text-soil' : 'text-muted-foreground'} ${className}`}>{deletionLabel(days)}</p>
}
