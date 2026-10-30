import { useQueryClient } from '@tanstack/react-query'
import { Download, LoaderCircle } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { getAnalysis } from '@/lib/api'
import { analysisKey } from '@/lib/query'

type Kind = 'polygons_png' | 'geojson'

const FILES: Record<Kind, { label: string; suffix: string }> = {
  polygons_png: { label: 'PNG com polígonos', suffix: 'areas-potenciais.png' },
  geojson: { label: 'GeoJSON', suffix: 'areas-potenciais.geojson' },
}

/** Downloads do resultado (R4.8). */
export function Downloads({ id, filename }: { id: string; filename: string }) {
  const queryClient = useQueryClient()
  const [busy, setBusy] = useState<Kind | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function download(kind: Kind) {
    setBusy(kind)
    setError(null)
    try {
      // URL assinada nova: a da tela pode ter expirado com a página aberta.
      const fresh = await queryClient.fetchQuery({
        queryKey: analysisKey(id),
        queryFn: () => getAnalysis(id),
        staleTime: 0,
      })
      const url = fresh.urls?.[kind]
      if (!url) throw new Error()
      // `<a download>` é ignorado entre origens; pelo blob o arquivo sai com o nome certo.
      const response = await fetch(url)
      if (!response.ok) throw new Error()
      save(await response.blob(), `${filename.replace(/\.tiff?$/i, '')}-${FILES[kind].suffix}`)
    } catch {
      setError('Não foi possível baixar o arquivo agora. Tente de novo.')
    } finally {
      setBusy(null)
    }
  }

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {(Object.keys(FILES) as Kind[]).map((kind) => (
          <Button key={kind} variant="outline" onClick={() => download(kind)} disabled={busy !== null}>
            {busy === kind ? <LoaderCircle className="animate-spin" aria-hidden /> : <Download aria-hidden />}
            {busy === kind ? 'Baixando…' : `Baixar ${FILES[kind].label}`}
          </Button>
        ))}
      </div>
      {error && (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  )
}

function save(blob: Blob, name: string) {
  const href = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = href
  link.download = name
  link.click()
  URL.revokeObjectURL(href)
}
