import { Link } from 'react-router'
import { Wordmark } from '@/components/Wordmark'
import { Button } from '@/components/ui/button'
import { supabase } from '@/lib/supabase'

export function AppHeader({ email }: { email: string | undefined }) {
  return (
    <header className="border-b border-border bg-background">
      <div className="mx-auto flex w-full max-w-screen-2xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <Link to="/" className="rounded-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50">
          <Wordmark />
        </Link>
        <div className="flex min-w-0 items-center gap-3">
          <span className="hidden truncate font-mono text-xs text-muted-foreground sm:inline">{email}</span>
          <Button variant="outline" onClick={() => supabase.auth.signOut()}>
            Sair
          </Button>
        </div>
      </div>
    </header>
  )
}
