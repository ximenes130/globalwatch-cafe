import { LoaderCircle } from 'lucide-react'
import { useServerWaking } from '@/lib/server-waking'

/** Aviso de servidor frio quando uma requisição passa de 5 s (R4.13). */
export function ServerWaking() {
  const waking = useServerWaking()

  return (
    <div aria-live="polite" className="pointer-events-none fixed inset-x-0 top-3 z-50 flex justify-center px-4">
      {waking && (
        <p className="pointer-events-auto flex items-center gap-2 rounded-full border border-border bg-card px-4 py-2 text-sm shadow-sm animate-in fade-in slide-in-from-top-1">
          <LoaderCircle className="size-4 animate-spin text-canopy" aria-hidden />
          Acordando o servidor, pode levar até um minuto.
        </p>
      )}
    </div>
  )
}
