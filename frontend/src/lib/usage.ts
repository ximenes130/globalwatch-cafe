import { useQuery } from '@tanstack/react-query'
import { getUsage } from '@/lib/api'
import { usageKey } from '@/lib/query'

export type QuotaKind = 'uploads' | 'messages'

export type Quota = { remaining: number; limit: number; resetsAt: string; blocked: boolean }

const DAY_MS = 24 * 60 * 60 * 1000
const time = new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit' })

export function useUsage() {
  // Sem novas tentativas: se falhar, os avisos somem e o 429 do backend continua valendo.
  return useQuery({ queryKey: usageKey, queryFn: getUsage, retry: false, staleTime: 30_000 })
}

/** Cota de um tipo, ou `null` enquanto não houver resposta do backend. */
export function useQuota(kind: QuotaKind): Quota | null {
  const { data } = useUsage()
  if (!data) return null
  const { used, limit } = data[kind]
  const remaining = Math.max(0, limit - used)
  return { remaining, limit, resetsAt: data.resets_at, blocked: remaining === 0 }
}

/** Hora local em que o contador volta a zero ("21:00" em Brasília para 0h UTC). */
export const formatResetTime = (iso: string) => time.format(new Date(iso))

/** "em 6 dias", "amanhã" ou "hoje", a partir do `created_at` do banco e da retenção da API. */
export function deletionDays(createdAt: string, retentionDays: number, now = Date.now()) {
  const left = new Date(createdAt).getTime() + retentionDays * DAY_MS - now
  return Math.max(0, Math.ceil(left / DAY_MS))
}

export function deletionLabel(days: number) {
  if (days <= 0) return 'Será apagada hoje'
  if (days === 1) return 'Será apagada amanhã'
  return `Será apagada em ${days} dias`
}
