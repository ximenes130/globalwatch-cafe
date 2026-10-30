import { MapPin } from 'lucide-react'
import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import type { ChatCard, ExclusionLevel, LimitationsCard, PolygonCard, SummaryCard } from '@/lib/api'
import { formatHa, formatImageDate, formatIndex } from '@/lib/format'

// Mesmos níveis da cascata do painel (N0 a N4), com o nome em português.
const LEVELS: Record<ExclusionLevel, { code: string; label: string }> = {
  no_data: { code: 'N0', label: 'Sem dado' },
  quality_mask: { code: 'N1', label: 'Máscara de qualidade' },
  low_vegetation: { code: 'N2', label: 'Vegetação baixa' },
  dense_canopy: { code: 'N3', label: 'Dossel denso' },
  low_chlorophyll: { code: 'N3b', label: 'Clorofila baixa' },
  high_amplitude: { code: 'N3c', label: 'Amplitude entre datas' },
  small_patch: { code: 'N4', label: 'Mancha pequena' },
}

const coordinate = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 6, maximumFractionDigits: 6 })
const LIMITATIONS_SHOWN = 3

/**
 * Dados que o assistente consultou para responder (R5.14). Vêm do retorno das
 * ferramentas, montados no backend: são a referência para conferir o texto.
 */
export type ShowPolygon = (id: number, centroid: [number, number]) => void

export function ChatCards({ cards, onShowPolygon }: { cards: ChatCard[]; onShowPolygon?: ShowPolygon }) {
  if (cards.length === 0) return null
  return (
    <section aria-label="Dados do processamento" className="space-y-2">
      <p className="font-mono text-[11px] tracking-wide text-muted-foreground uppercase">Dados do processamento</p>
      {cards.map((card, i) => {
        // Tipo desconhecido (backend mais novo que o front): não mostra nada.
        if (card.kind === 'summary') return <Summary key={i} card={card} />
        if (card.kind === 'polygon') return <Polygon key={i} card={card} onShow={onShowPolygon} />
        if (card.kind === 'limitations') return <Limitations key={i} card={card} />
        return null
      })}
    </section>
  )
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <article className="rounded-lg border border-border bg-card px-3.5 py-3 text-sm">
      <h3 className="font-mono text-xs text-muted-foreground">{title}</h3>
      <div className="mt-2">{children}</div>
    </article>
  )
}

function Summary({ card: { data } }: { card: SummaryCard }) {
  const excluded = (Object.keys(LEVELS) as ExclusionLevel[]).filter((level) => (data.excluded_area_ha[level] ?? 0) > 0)
  const { ndvi_min, ndvi_max, min_area_ha, ndvi_amplitude_max } = data.thresholds
  return (
    <Card title="Resumo da análise">
      <p className="font-mono text-xs text-muted-foreground">
        {data.acquired_at && <>Imagem de {formatImageDate(data.acquired_at)}</>}
        {data.second_acquired_at && <> · segunda data {formatImageDate(data.second_acquired_at)}</>}
      </p>
      <p className="mt-1.5 flex flex-wrap items-baseline gap-x-2">
        <span className="font-mono text-xl text-cherry tabular-nums">{formatHa(data.potential_area_ha)} ha</span>
        <span className="text-muted-foreground">
          de área potencial em {data.polygon_count} {data.polygon_count === 1 ? 'polígono' : 'polígonos'}
        </span>
      </p>
      <Rows
        rows={[
          ['Área total', `${formatHa(data.total_area_ha)} ha`],
          ['Área válida', `${formatHa(data.valid_area_ha)} ha`],
          ['Máscara de qualidade', `${formatHa(data.masked_area_ha)} ha`],
        ]}
      />
      {excluded.length > 0 && (
        <>
          <p className="mt-3 text-xs text-muted-foreground">Excluído em cada nível</p>
          <Rows rows={excluded.map((level) => [`${LEVELS[level].code} · ${LEVELS[level].label}`, `${formatHa(data.excluded_area_ha[level]!)} ha`])} />
        </>
      )}
      <p className="mt-3 font-mono text-[11px] text-muted-foreground">
        NDVI {formatIndex(ndvi_min)} a {formatIndex(ndvi_max)} · mancha mínima {formatHa(min_area_ha)} ha
        {ndvi_amplitude_max !== undefined && <> · amplitude abaixo de {formatIndex(ndvi_amplitude_max)}</>}
      </p>
    </Card>
  )
}

function Polygon({ card: { data }, onShow }: { card: PolygonCard; onShow?: ShowPolygon }) {
  const [lon, lat] = data.centroid
  return (
    <Card title={`Área potencial nº ${data.id}`}>
      <Rows
        rows={[
          ['Área', `${formatHa(data.area_ha)} ha`],
          ['NDVI médio', formatIndex(data.ndvi_mean)],
          ...(data.gndvi_mean !== null ? [['GNDVI médio', formatIndex(data.gndvi_mean)] as [string, string]] : []),
        ]}
      />
      {/* Linha própria: a coordenada é longa e espremeria os rótulos ao lado. */}
      <p className="mt-2 font-mono text-[11px] text-muted-foreground">
        Centróide lat {coordinate.format(lat)} · lon {coordinate.format(lon)}
      </p>
      <div className="mt-1 flex items-center justify-between gap-2">
        <p className="text-[11px] text-muted-foreground">Não validada em campo.</p>
        {onShow && (
          <Button size="xs" variant="outline" onClick={() => onShow(data.id, data.centroid)}>
            <MapPin /> Ver no mapa
          </Button>
        )}
      </div>
    </Card>
  )
}

function Limitations({ card: { data } }: { card: LimitationsCard }) {
  const shown = data.items.slice(0, LIMITATIONS_SHOWN)
  const rest = data.items.slice(LIMITATIONS_SHOWN)
  return (
    <Card title="Limitações do método">
      <ul className="list-disc space-y-1 pl-4 text-muted-foreground marker:text-border">
        {shown.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      {rest.length > 0 && (
        <details className="group mt-1">
          <summary className="cursor-pointer text-xs text-foreground underline-offset-2 hover:underline">
            <span className="group-open:hidden">Mais {rest.length} {rest.length === 1 ? 'limitação' : 'limitações'}</span>
            <span className="hidden group-open:inline">Mostrar menos</span>
          </summary>
          <ul className="mt-1 list-disc space-y-1 pl-4 text-muted-foreground marker:text-border">
            {rest.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </details>
      )}
      {data.references.length > 0 && (
        <ul className="mt-3 space-y-1 border-t border-border pt-2 text-xs text-muted-foreground">
          {data.references.map((ref) => (
            <li key={ref.doi}>
              {ref.citation}{' '}
              <a className="text-foreground underline-offset-2 hover:underline" href={`https://doi.org/${ref.doi}`} target="_blank" rel="noreferrer">
                doi:{ref.doi}
              </a>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

function Rows({ rows }: { rows: [string, string][] }) {
  return (
    <dl className="mt-2 grid grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-1">
      {rows.map(([label, value]) => (
        <div key={label} className="contents">
          <dt className="truncate text-muted-foreground">{label}</dt>
          <dd className="text-right font-mono tabular-nums">{value}</dd>
        </div>
      ))}
    </dl>
  )
}
