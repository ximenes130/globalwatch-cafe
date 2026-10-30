import { QueryClient } from '@tanstack/react-query'
import { ApiError } from '@/lib/api'

// Erro 4xx não melhora repetindo; rede e 5xx (servidor acordando) ganham 2 novas tentativas.
const retryable = (error: Error) =>
  !(error instanceof ApiError && error.status >= 400 && error.status < 500)

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failures, error) => retryable(error) && failures < 2,
      staleTime: 10_000,
    },
  },
})

export const analysesKey = ['analyses'] as const
export const analysisKey = (id: string) => ['analyses', id] as const
export const usageKey = ['usage'] as const
