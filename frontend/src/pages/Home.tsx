import type { Session } from '@supabase/supabase-js'
import { useCallback, useEffect, useState } from 'react'
import { Wordmark } from '@/components/Wordmark'
import { Button } from '@/components/ui/button'
import { getMe, type Me } from '@/lib/api'
import { supabase } from '@/lib/supabase'

type MeState = { kind: 'loading' } | { kind: 'ok'; me: Me } | { kind: 'error'; message: string }

// Provisória: a lista de análises (spec 004, T4.2) substitui esta tela.
export function Home({ session }: { session: Session }) {
  const [state, setState] = useState<MeState>({ kind: 'loading' })

  const fetchMe = useCallback(() => {
    getMe()
      .then((me) => setState({ kind: 'ok', me }))
      .catch((error: Error) => setState({ kind: 'error', message: error.message }))
  }, [])

  useEffect(fetchMe, [fetchMe])

  function retry() {
    setState({ kind: 'loading' })
    fetchMe()
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="border-b border-border">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-8">
          <Wordmark />
          <div className="flex min-w-0 items-center gap-3">
            <span className="hidden truncate font-mono text-xs text-muted-foreground sm:inline">
              {session.user.email}
            </span>
            <Button variant="outline" onClick={() => supabase.auth.signOut()}>
              Sair
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-8">
        <h1 className="font-heading text-4xl font-[640] tracking-tight [font-stretch:75%]">
          Suas análises
        </h1>

        <div className="mt-6 max-w-md rounded-lg border border-border bg-card p-5" aria-live="polite">
          {state.kind === 'loading' && (
            <div className="space-y-2" aria-label="Carregando sua conta">
              <div className="h-3 w-24 animate-pulse rounded bg-muted" />
              <div className="h-4 w-56 animate-pulse rounded bg-muted" />
            </div>
          )}
          {state.kind === 'ok' && (
            <>
              <p className="font-mono text-xs text-muted-foreground">Conta verificada pelo servidor</p>
              <p className="mt-1 truncate font-medium">{state.me.email}</p>
            </>
          )}
          {state.kind === 'error' && (
            <div role="alert" className="space-y-3">
              <p className="text-sm">{state.message}</p>
              <Button variant="outline" onClick={retry}>
                Tentar de novo
              </Button>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
