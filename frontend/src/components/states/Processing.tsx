import { LoaderCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { formatElapsed } from '@/lib/format'

/** Análise em `processing`: tempo decorrido desde o envio, sem porcentagem inventada (R4.4). */
export function Processing({ filename, createdAt }: { filename: string; createdAt: string }) {
  const elapsed = useElapsedSeconds(createdAt)

  return (
    <div className="rounded-lg border border-border bg-card" aria-live="polite">
      <div className="h-0.5 overflow-hidden rounded-t-lg bg-muted" aria-hidden>
        <div className="h-full w-1/4 animate-indeterminate bg-canopy" />
      </div>
      <div className="p-5">
        <p className="flex items-center gap-2 font-medium">
          <LoaderCircle className="size-4 animate-spin text-canopy" aria-hidden />
          Processando a imagem
        </p>
        <p className="mt-1 truncate font-mono text-xs text-muted-foreground" title={filename}>
          {filename}
        </p>
        <p className="mt-4 font-heading text-3xl font-[600] tabular-nums [font-stretch:80%]" aria-label={`Tempo decorrido: ${formatElapsed(elapsed)}`}>
          {formatElapsed(elapsed)}
        </p>
        <p className="mt-3 max-w-prose text-sm text-muted-foreground">
          O recorte do kit leva alguns segundos. Se o servidor estava dormindo, pode levar até um
          minuto. Você pode sair desta tela: a análise continua e aparece na sua lista.
        </p>
      </div>
    </div>
  )
}

function useElapsedSeconds(since: string) {
  const start = new Date(since).getTime()
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [])

  // Relógio do navegador e do servidor podem divergir um pouco: nunca negativo.
  return Math.max(0, Math.floor((now - start) / 1000))
}
