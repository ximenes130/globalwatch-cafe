import { useState } from 'react'
import { GoogleIcon } from '@/components/GoogleIcon'
import { NdviRuler } from '@/components/NdviRuler'
import { Wordmark } from '@/components/Wordmark'
import { Button } from '@/components/ui/button'
import { supabase } from '@/lib/supabase'

type Status = 'idle' | 'redirecting' | 'error'

export function Login() {
  const [status, setStatus] = useState<Status>('idle')

  async function signIn() {
    setStatus('redirecting')
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: window.location.origin },
    })
    if (error) setStatus('error')
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="mx-auto flex w-full max-w-6xl items-baseline justify-between gap-4 px-4 py-5 sm:px-8">
        <Wordmark />
        <span className="font-mono text-xs text-muted-foreground">Sentinel-2 L2A · 10 m</span>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col justify-center gap-14 px-4 py-10 sm:px-8 sm:py-16">
        <section className="max-w-3xl">
          <h1 className="font-heading text-[clamp(2.75rem,9vw,6.25rem)] leading-[0.92] font-[640] tracking-[-0.015em] text-balance [font-stretch:70%]">
            Onde pode haver <span className="text-cherry">café</span> nesta imagem?
          </h1>
          <p className="mt-6 max-w-xl text-lg text-pretty text-muted-foreground">
            Envie um recorte Sentinel-2. O Global Watch calcula índices espectrais, desenha as
            áreas com assinatura compatível com cafezal e responde perguntas sobre elas, com a
            área em hectares e as limitações à vista.
          </p>

          <div className="mt-9 flex flex-col items-start gap-3">
            <Button
              size="lg"
              onClick={signIn}
              disabled={status === 'redirecting'}
              className="h-12 gap-3 px-5 text-base"
            >
              <GoogleIcon />
              {status === 'redirecting' ? 'Abrindo o Google…' : 'Entrar com Google'}
            </Button>
            {status === 'error' ? (
              <p role="alert" className="text-sm text-destructive">
                Não foi possível abrir o login do Google. Tente de novo.
              </p>
            ) : (
              <p className="text-sm text-muted-foreground">
                O primeiro acesso cria sua conta. Usamos apenas nome e e-mail.
              </p>
            )}
          </div>
        </section>

        <figure className="w-full">
          <NdviRuler />
          <figcaption className="mt-4 max-w-2xl font-mono text-xs leading-relaxed text-muted-foreground">
            NDVI típico na estação seca. A faixa marcada indica área potencial, não café
            confirmado em campo.
          </figcaption>
        </figure>
      </main>
    </div>
  )
}
