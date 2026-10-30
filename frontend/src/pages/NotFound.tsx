import { Link } from 'react-router'
import { Button } from '@/components/ui/button'

export function NotFound() {
  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-8">
      <h1 className="font-heading text-4xl font-[640] tracking-tight [font-stretch:75%]">
        Página não encontrada
      </h1>
      <p className="mt-2 text-muted-foreground">O endereço não corresponde a nenhuma tela.</p>
      <Button asChild variant="outline" className="mt-6">
        <Link to="/">Ver suas análises</Link>
      </Button>
    </main>
  )
}
