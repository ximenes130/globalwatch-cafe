import { useId } from 'react'
import type { Overlay } from '@/components/MapView'
import type { Stats } from '@/lib/api'
import { formatHa } from '@/lib/format'

type Props = {
  stats: Stats
  overlay: Overlay
  onOverlayChange: (overlay: Overlay) => void
  opacity: number
  onOpacityChange: (opacity: number) => void
}

const OVERLAYS: { value: Overlay; label: string }[] = [
  { value: 'rgb', label: 'Cor verdadeira' },
  { value: 'classification', label: 'Classificação' },
]

/** Legenda e controles da camada do mapa (R4.6, R4.10). */
export function Legend({ stats, overlay, onOverlayChange, opacity, onOpacityChange }: Props) {
  const opacityId = useId()

  return (
    <div className="space-y-4">
      <ul className="space-y-1.5 text-sm" aria-label="Legenda do mapa">
        <li className="flex items-center gap-2.5">
          <span className="size-3.5 rounded-[3px] border-[1.5px] border-cherry bg-cherry/20" aria-hidden />
          Área potencial de café
        </li>
        <li className="flex items-center gap-2.5">
          <span className="size-3.5 rounded-[3px] bg-[#6b7280]/65" aria-hidden />
          <span>
            Área mascarada <span className="text-muted-foreground">(nuvem, sombra, água)</span>
          </span>
          <span className="ml-auto font-mono text-xs text-muted-foreground tabular-nums">
            {formatHa(stats.masked_area_ha)} ha
          </span>
        </li>
        <li className="flex items-center gap-2.5">
          <span className="h-0 w-3.5 border-t-[1.5px] border-dashed border-foreground" aria-hidden />
          Limite da imagem
        </li>
      </ul>

      <div className="flex flex-wrap items-end gap-x-5 gap-y-3">
        <div role="group" aria-label="Imagem sob os polígonos" className="inline-flex rounded-lg border border-border bg-muted p-0.5">
          {OVERLAYS.map((option) => (
            <button
              key={option.value}
              type="button"
              aria-pressed={overlay === option.value}
              onClick={() => onOverlayChange(option.value)}
              className="rounded-md px-2.5 py-1 text-sm text-muted-foreground transition-colors outline-none hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 aria-pressed:bg-card aria-pressed:text-foreground aria-pressed:ring-1 aria-pressed:ring-border"
            >
              {option.label}
            </button>
          ))}
        </div>
        <label htmlFor={opacityId} className="flex min-w-40 flex-1 flex-col gap-1 text-xs text-muted-foreground">
          <span className="flex justify-between">
            Opacidade da imagem
            <span className="font-mono tabular-nums">{Math.round(opacity * 100)}%</span>
          </span>
          <input
            id={opacityId}
            type="range"
            min={0}
            max={100}
            step={5}
            value={Math.round(opacity * 100)}
            onChange={(event) => onOpacityChange(Number(event.target.value) / 100)}
            className="w-full accent-canopy"
          />
        </label>
      </div>
      {overlay === 'classification' && (
        <p className="text-xs text-muted-foreground">
          Na classificação, a área potencial aparece preenchida e a área mascarada em cinza; o resto
          da imagem fica transparente.
        </p>
      )}
    </div>
  )
}
