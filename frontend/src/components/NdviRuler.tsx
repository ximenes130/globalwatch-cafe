import { CANDIDATE_NDVI, NDVI_SCALE } from '@/lib/method'

const TICKS = [-0.2, 0, 0.2, 0.4, 0.6, 0.8, 1]

// Coberturas típicas na estação seca do sul de Minas; premissa do método, não medição.
const TYPICAL_COVERS = [
  { label: 'solo exposto', ndvi: 0.08 },
  { label: 'pasto seco', ndvi: 0.32 },
  { label: 'mata', ndvi: 0.9 },
]

const toPercent = (ndvi: number) =>
  ((ndvi - NDVI_SCALE.min) / (NDVI_SCALE.max - NDVI_SCALE.min)) * 100

const formatNdvi = (ndvi: number) =>
  ndvi.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 2 })

/** Régua de NDVI com a faixa candidata marcada: o método em uma imagem. */
export function NdviRuler() {
  const start = toPercent(CANDIDATE_NDVI.min)
  const width = toPercent(CANDIDATE_NDVI.max) - start

  return (
    <div
      role="img"
      aria-label={`Escala de NDVI de ${formatNdvi(NDVI_SCALE.min)} a ${formatNdvi(NDVI_SCALE.max)}. Faixa candidata a café entre ${formatNdvi(CANDIDATE_NDVI.min)} e ${formatNdvi(CANDIDATE_NDVI.max)}, abaixo da mata e acima do pasto seco.`}
      className="relative w-full select-none pt-7"
    >
      {/* Alinhado ao fim da faixa: assim não sai da tela no celular. */}
      <span
        className="absolute top-0 font-mono text-[11px] leading-none whitespace-nowrap text-cherry"
        style={{ right: `${100 - start - width}%` }}
      >
        faixa candidata a café
      </span>

      <div className="relative h-14 overflow-hidden rounded-sm animate-in fade-in duration-700 sm:h-16">
        <div className="absolute inset-0 bg-linear-to-r from-soil via-straw via-45% to-canopy" />
        <div className="absolute inset-y-0 left-[58%] w-[42%] bg-linear-to-r from-transparent to-canopy/70" />
        <div
          className="absolute inset-y-0 animate-in fade-in zoom-in-y-50 border-2 border-cherry delay-300 duration-500 fill-mode-both [background:repeating-linear-gradient(135deg,color-mix(in_oklch,var(--cherry)_28%,transparent)_0_2px,transparent_2px_7px)]"
          style={{ left: `${start}%`, width: `${width}%` }}
        />
      </div>

      <div className="relative h-6 font-mono text-[11px] text-muted-foreground">
        {TICKS.map((tick) => (
          <span
            key={tick}
            className="absolute top-1.5 -translate-x-1/2 tabular-nums first:translate-x-0 last:-translate-x-full"
            style={{ left: `${toPercent(tick)}%` }}
          >
            {formatNdvi(tick)}
          </span>
        ))}
      </div>

      <div className="relative mt-1 hidden h-5 text-xs text-muted-foreground sm:block">
        {TYPICAL_COVERS.map((cover) => (
          <span
            key={cover.label}
            className="absolute -translate-x-1/2 whitespace-nowrap"
            style={{ left: `${toPercent(cover.ndvi)}%` }}
          >
            {cover.label}
          </span>
        ))}
      </div>
    </div>
  )
}
