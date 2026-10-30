import type { Stats } from '@/lib/api'
import { formatHa } from '@/lib/format'

/** Legenda das camadas do mapa (R4.6). */
export function Legend({ stats }: { stats: Stats }) {
  return (
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
  )
}
