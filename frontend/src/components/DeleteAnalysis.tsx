import { useMutation, useQueryClient } from '@tanstack/react-query'
import { LoaderCircle, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router'
import { AlertDialog } from 'radix-ui'
import { Button } from '@/components/ui/button'
import { deleteAnalysis } from '@/lib/api'
import { analysesKey, analysisKey } from '@/lib/query'

/** Apagar com confirmação (R4.11): some a linha, os arquivos e a conversa. */
export function DeleteAnalysis({ id, filename }: { id: string; filename: string }) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const remove = useMutation({
    mutationFn: () => deleteAnalysis(id),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: analysisKey(id) })
      queryClient.invalidateQueries({ queryKey: analysesKey, exact: true })
      navigate('/')
    },
  })

  return (
    <AlertDialog.Root
      open={open}
      onOpenChange={(next) => {
        if (remove.isPending) return
        setOpen(next)
        if (!next) remove.reset()
      }}
    >
      <AlertDialog.Trigger asChild>
        <Button variant="ghost" className="text-muted-foreground hover:text-destructive">
          <Trash2 aria-hidden />
          Apagar análise
        </Button>
      </AlertDialog.Trigger>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="fixed inset-0 z-50 bg-foreground/30 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:animate-in data-[state=open]:fade-in-0" />
        <AlertDialog.Content className="fixed top-1/2 left-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg border border-border bg-card p-5 shadow-lg data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95">
          <AlertDialog.Title className="font-heading text-xl font-[620] tracking-tight [font-stretch:80%]">
            Apagar esta análise?
          </AlertDialog.Title>
          <AlertDialog.Description className="mt-2 text-sm text-muted-foreground">
            <span className="font-medium break-all text-foreground">{filename}</span>, as imagens geradas, o
            GeoJSON e a conversa serão apagados. Não dá para desfazer.
          </AlertDialog.Description>
          {remove.isError && (
            <p role="alert" className="mt-3 text-sm text-destructive">
              {remove.error.message}
            </p>
          )}
          <div className="mt-5 flex justify-end gap-2">
            <AlertDialog.Cancel asChild>
              <Button variant="outline" disabled={remove.isPending}>
                Cancelar
              </Button>
            </AlertDialog.Cancel>
            {/* Botão comum, não `Action`: o diálogo só fecha quando a API confirmar. */}
            <Button variant="destructive" onClick={() => remove.mutate()} disabled={remove.isPending}>
              {remove.isPending ? <LoaderCircle className="animate-spin" aria-hidden /> : <Trash2 aria-hidden />}
              {remove.isPending ? 'Apagando…' : 'Apagar'}
            </Button>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  )
}
