import { RotateCw } from 'lucide-react'
import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { ApiError } from '@/lib/api'

type Props = {
  error: Error
  title?: string
  /** Substitui a mensagem do erro quando o título já diz o mesmo. */
  message?: string
  /** Sem `onRetry`, não há botão: o erro não se resolve tentando de novo (ex.: 404). */
  onRetry?: () => void
  retrying?: boolean
  children?: ReactNode
}

/** Erro compreensível com ação de tentar de novo (R4.14). */
export function ErrorState({ error, title, message, onRetry, retrying = false, children }: Props) {
  const limited = error instanceof ApiError && error.status === 429

  return (
    <div role="alert" className="rounded-lg border border-border bg-card p-5">
      <p className="font-medium">
        {title ?? (limited ? 'Limite diário atingido' : 'Não foi possível carregar')}
      </p>
      <p className="mt-1 max-w-prose text-sm text-muted-foreground">{message ?? error.message}</p>
      {limited && (
        <p className="mt-1 text-sm text-muted-foreground">O limite volta a zero à meia-noite (UTC).</p>
      )}
      {(onRetry || children) && (
        <div className="mt-4 flex flex-wrap gap-2">
          {onRetry && (
            <Button variant="outline" onClick={onRetry} disabled={retrying}>
              <RotateCw className={retrying ? 'animate-spin' : undefined} />
              {retrying ? 'Tentando…' : 'Tentar de novo'}
            </Button>
          )}
          {children}
        </div>
      )}
    </div>
  )
}
