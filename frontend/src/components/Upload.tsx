import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ChevronRight, FileImage, Upload as UploadIcon, X } from 'lucide-react'
import { type DragEvent, type FormEvent, useId, useState } from 'react'
import { useNavigate } from 'react-router'
import { ErrorState } from '@/components/states/ErrorState'
import { Button } from '@/components/ui/button'
import { createAnalysis, type UploadFiles } from '@/lib/api'
import { formatIndex } from '@/lib/format'
import { NDVI_AMPLITUDE_MAX } from '@/lib/method'
import { analysesKey } from '@/lib/query'
import { formatSize, MAX_UPLOAD_MB, rejectReason, splitDropped } from '@/lib/upload'

type Slot = keyof UploadFiles
type Selection = Record<Slot, File | null>

const EMPTY: Selection = { image: null, scl: null, image2: null, scl2: null }

/** Envio da imagem com SCL e segunda data opcionais (R4.3, R4.4, R3.10). */
export function Upload() {
  const [files, setFiles] = useState<Selection>(EMPTY)
  const [rejected, setRejected] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const upload = useMutation({
    mutationFn: (selected: UploadFiles) => createAnalysis(selected, setProgress),
    onSuccess: ({ id }) => {
      queryClient.invalidateQueries({ queryKey: analysesKey })
      navigate(`/analyses/${id}`)
    },
  })
  const busy = upload.isPending

  /** Aceita os arquivos válidos e mostra o motivo do primeiro recusado. */
  function choose(chosen: Partial<Selection>) {
    upload.reset()
    const accepted: Partial<Selection> = {}
    let reason: string | null = null
    for (const [slot, file] of Object.entries(chosen) as [Slot, File | null][]) {
      const problem = file && rejectReason(file)
      if (problem) reason ??= problem
      else accepted[slot] = file
    }
    setRejected(reason)
    setFiles((current) => {
      const next = { ...current, ...accepted }
      // A SCL da segunda data não vale sem a segunda imagem (o backend responde 422).
      if (!next.image2) next.scl2 = null
      return next
    })
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    const { image } = files
    if (!image || busy) return
    setProgress(0)
    upload.mutate({ ...files, image })
  }

  return (
    <form onSubmit={submit} className="rounded-lg border border-border bg-card p-4 sm:p-5" aria-label="Nova análise">
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,18rem)]">
        <DropZone file={files.image} disabled={busy} onFiles={(dropped) => choose(splitDropped(dropped))} onClear={() => choose({ image: null })} />

        <div className="flex flex-col gap-4">
          <FileField
            label="Camada de qualidade SCL"
            hint="Opcional. Sem ela, nuvem e sombra não são mascaradas."
            file={files.scl}
            disabled={busy}
            onChange={(scl) => choose({ scl })}
          />
          <details className="group rounded-md border border-border px-3 py-2 open:pb-3">
            <summary className="flex cursor-pointer list-none items-center gap-1.5 text-sm font-medium outline-none select-none focus-visible:ring-3 focus-visible:ring-ring/50 [&::-webkit-details-marker]:hidden">
              <ChevronRight className="size-4 transition-transform duration-150 group-open:rotate-90" aria-hidden />
              Segunda data (opcional)
            </summary>
            <p className="mt-2 text-xs text-muted-foreground">
              A mesma área em outra data, de preferência na chuva. Sai da área potencial o pixel cujo
              NDVI muda {formatIndex(NDVI_AMPLITUDE_MAX)} ou mais entre as datas.
            </p>
            <div className="mt-3 flex flex-col gap-3">
              <FileField label="Imagem da segunda data" file={files.image2} disabled={busy} onChange={(image2) => choose({ image2 })} />
              <FileField
                label="SCL da segunda data"
                file={files.scl2}
                disabled={busy || !files.image2}
                onChange={(scl2) => choose({ scl2 })}
              />
            </div>
          </details>
        </div>
      </div>

      {rejected && (
        <p role="alert" className="mt-4 text-sm text-destructive">
          {rejected}
        </p>
      )}
      {upload.isError && (
        <div className="mt-4">
          <ErrorState error={upload.error} title="O envio não foi aceito" />
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-4">
        <Button type="submit" size="lg" disabled={!files.image || busy} className="px-4">
          <UploadIcon />
          {busy ? 'Enviando…' : 'Analisar imagem'}
        </Button>
        {busy && <UploadProgress fraction={progress} />}
      </div>
    </form>
  )
}

function UploadProgress({ fraction }: { fraction: number }) {
  const percent = Math.round(fraction * 100)
  return (
    <div className="flex min-w-48 flex-1 items-center gap-3" aria-live="polite">
      <div
        role="progressbar"
        aria-label="Envio do arquivo"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted"
      >
        <div className="h-full origin-left rounded-full bg-canopy transition-transform duration-200" style={{ transform: `scaleX(${fraction})` }} />
      </div>
      <span className="w-28 font-mono text-xs text-muted-foreground tabular-nums">
        {percent < 100 ? `${percent}% enviado` : 'Aguardando…'}
      </span>
    </div>
  )
}

type DropZoneProps = {
  file: File | null
  disabled: boolean
  onFiles: (files: File[]) => void
  onClear: () => void
}

function DropZone({ file, disabled, onFiles, onClear }: DropZoneProps) {
  const [over, setOver] = useState(false)
  const id = useId()

  function handleDrop(event: DragEvent) {
    event.preventDefault()
    setOver(false)
    if (!disabled) onFiles([...event.dataTransfer.files])
  }

  if (file) {
    return (
      <div className="flex min-h-36 items-center gap-3 rounded-md border border-border bg-background px-4">
        <FileImage className="size-7 shrink-0 text-canopy" aria-hidden />
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium" title={file.name}>{file.name}</p>
          <p className="font-mono text-xs text-muted-foreground">{formatSize(file.size)}</p>
        </div>
        <Button type="button" variant="ghost" size="icon" onClick={onClear} disabled={disabled} aria-label={`Remover ${file.name}`}>
          <X />
        </Button>
      </div>
    )
  }

  return (
    <label
      htmlFor={id}
      onDragOver={(event) => {
        event.preventDefault()
        setOver(true)
      }}
      onDragLeave={() => setOver(false)}
      onDrop={handleDrop}
      data-over={over || undefined}
      className="flex min-h-36 cursor-pointer flex-col items-center justify-center gap-2 rounded-md border border-dashed border-input bg-background px-4 py-6 text-center transition-colors duration-150 has-focus-visible:ring-3 has-focus-visible:ring-ring/50 hover:border-canopy/60 data-over:border-solid data-over:border-canopy data-over:bg-canopy/5"
    >
      <UploadIcon className="size-6 text-muted-foreground" aria-hidden />
      <span className="font-medium">Arraste a imagem Sentinel-2 aqui ou escolha o arquivo</span>
      <span className="text-sm text-muted-foreground">
        GeoTIFF com B02, B03, B04 e B08, até {MAX_UPLOAD_MB} MB. Solte a SCL junto, se tiver.
      </span>
      <input
        id={id}
        type="file"
        accept=".tif,.tiff,image/tiff"
        multiple
        className="sr-only"
        disabled={disabled}
        onChange={(event) => {
          onFiles([...(event.target.files ?? [])])
          event.target.value = ''
        }}
      />
    </label>
  )
}

type FileFieldProps = {
  label: string
  hint?: string
  file: File | null
  disabled: boolean
  onChange: (file: File | null) => void
}

function FileField({ label, hint, file, disabled, onChange }: FileFieldProps) {
  const id = useId()
  return (
    <div>
      <p className="text-sm font-medium">{label}</p>
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      <div className="mt-1.5 flex min-h-9 items-center gap-2">
        {file ? (
          <>
            <span className="min-w-0 flex-1 truncate font-mono text-xs" title={file.name}>
              {file.name} · {formatSize(file.size)}
            </span>
            <Button type="button" variant="ghost" size="icon-sm" onClick={() => onChange(null)} disabled={disabled} aria-label={`Remover ${file.name}`}>
              <X />
            </Button>
          </>
        ) : (
          <label
            htmlFor={id}
            aria-disabled={disabled}
            className="inline-flex h-8 cursor-pointer items-center rounded-lg border border-border bg-background px-2.5 text-sm transition-colors has-focus-visible:ring-3 has-focus-visible:ring-ring/50 hover:bg-muted aria-disabled:pointer-events-none aria-disabled:opacity-50"
          >
            Escolher arquivo
            <input
              id={id}
              type="file"
              accept=".tif,.tiff,image/tiff"
              className="sr-only"
              disabled={disabled}
              onChange={(event) => {
                onChange(event.target.files?.[0] ?? null)
                event.target.value = ''
              }}
            />
          </label>
        )}
      </div>
    </div>
  )
}
