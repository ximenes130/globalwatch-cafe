import { TriangleAlert } from 'lucide-react'
import type { ReactNode } from 'react'
import type { Analysis, Rationale, RationaleStep, Stats } from '@/lib/api'
import { formatHa, formatImageDate, formatPercent } from '@/lib/format'

type Props = {
  analysis: Analysis
  stats: Stats
  rationale: Rationale
  legend: ReactNode
  actions: ReactNode
  footer: ReactNode
}

/** Números, datas, aviso e justificativa da análise (R4.6, R4.9, R4.15). */
export function Summary({ analysis, stats, rationale, legend, actions, footer }: Props) {
  const empty = stats.polygon_count === 0

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs text-muted-foreground">
          {analysis.acquired_at && <>Imagem de {formatImageDate(analysis.acquired_at)}</>}
          {stats.second_acquired_at && <> · segunda data {formatImageDate(stats.second_acquired_at)}</>}
        </p>
        <p className="mt-0.5 truncate text-sm" title={analysis.filename}>{analysis.filename}</p>
      </header>

      {empty ? <NoPotentialArea /> : <Headline stats={stats} />}

      <dl className="grid grid-cols-3 divide-x divide-border rounded-lg border border-border bg-card">
        <Stat label="Área potencial" value={formatHa(stats.potential_area_ha)} unit="ha" detail={formatPercent(stats.potential_area_ha, stats.total_area_ha)} />
        <Stat label="Área total" value={formatHa(stats.total_area_ha)} unit="ha" />
        <Stat label="Polígonos" value={String(stats.polygon_count)} />
      </dl>

      <Notice />

      {actions}

      <section aria-labelledby="legend-title">
        <h2 id="legend-title" className="mb-2 font-mono text-[11px] tracking-wide text-muted-foreground uppercase">
          Legenda
        </h2>
        {legend}
      </section>

      <Cascade stats={stats} rationale={rationale} />
      <Limitations items={rationale.limitations} />
      <References rationale={rationale} />
      {footer}
    </div>
  )
}

function Headline({ stats }: { stats: Stats }) {
  const share = stats.total_area_ha > 0 ? stats.potential_area_ha / stats.total_area_ha : 0
  return (
    <div>
      <p className="font-heading text-[2.75rem] leading-none font-[640] tracking-tight tabular-nums [font-stretch:72%]">
        {formatHa(stats.potential_area_ha)}
        <span className="ml-1.5 font-mono text-base font-normal text-muted-foreground">ha</span>
      </p>
      <p className="mt-1.5 text-sm text-muted-foreground">
        de área potencial de café, {formatPercent(stats.potential_area_ha, stats.total_area_ha)} do recorte
      </p>
      {/* Parte do todo: só a área potencial tem cor; o resto do recorte fica neutro. */}
      <div className="mt-3 flex h-2 gap-0.5" aria-hidden>
        <div className="rounded-l-sm bg-cherry" style={{ width: `${share * 100}%` }} />
        <div className="flex-1 rounded-r-sm bg-muted" />
      </div>
    </div>
  )
}

function NoPotentialArea() {
  return (
    <div role="status">
      <p className="font-heading text-3xl leading-tight font-[640] tracking-tight [font-stretch:75%]">
        Nenhuma área potencial encontrada
      </p>
      <p className="mt-1.5 text-sm text-muted-foreground">
        Nenhum trecho da imagem passou por todos os critérios. A lista “Como a área foi
        delimitada”, abaixo, mostra quanto cada critério excluiu.
      </p>
    </div>
  )
}

function Stat({ label, value, unit, detail }: { label: string; value: string; unit?: string; detail?: string }) {
  return (
    <div className="min-w-0 px-3 py-2.5">
      <dt className="truncate text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 font-medium tabular-nums">
        {value}
        {unit && <span className="ml-1 font-mono text-[11px] text-muted-foreground">{unit}</span>}
        {detail && <span className="block font-mono text-[11px] text-muted-foreground">{detail}</span>}
      </dd>
    </div>
  )
}

function Notice() {
  return (
    <aside className="flex gap-2.5 rounded-lg border border-straw bg-straw/20 px-3.5 py-3 text-sm" aria-label="Aviso sobre o resultado">
      <TriangleAlert className="mt-0.5 size-4 shrink-0 text-soil" aria-hidden />
      <p>
        <strong className="font-medium">Resultado potencial, não validado em campo.</strong>{' '}
        As áreas têm assinatura espectral compatível com cafezal; não são café confirmado, e
        a classificação não tem acurácia medida.
      </p>
    </aside>
  )
}

/** A cascata de critérios com o quanto cada um excluiu; cada barra é a fração do recorte. */
function Cascade({ stats, rationale }: { stats: Stats; rationale: Rationale }) {
  const total = stats.total_area_ha
  return (
    <section aria-labelledby="cascade-title">
      <h2 id="cascade-title" className="font-heading text-xl font-[620] tracking-tight [font-stretch:80%]">
        Como a área foi delimitada
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">{rationale.summary}</p>
      <ol className="mt-4 space-y-3">
        {rationale.steps.map((step) => (
          <CascadeRow key={step.name} step={step} total={total} />
        ))}
        <li className="border-t border-border pt-3">
          <div className="flex items-baseline justify-between gap-3">
            <span className="font-medium">Área potencial</span>
            <span className="font-mono text-sm tabular-nums">{formatHa(stats.potential_area_ha)} ha</span>
          </div>
          <Bar fraction={stats.potential_area_ha / total} highlight />
        </li>
      </ol>
    </section>
  )
}

function CascadeRow({ step, total }: { step: RationaleStep; total: number }) {
  return (
    <li>
      <div className="flex items-baseline gap-2">
        <span className="w-8 shrink-0 font-mono text-[11px] text-muted-foreground">{step.level}</span>
        <span className="min-w-0 flex-1 font-mono text-xs">{step.rule}</span>
        <span className="shrink-0 font-mono text-sm tabular-nums">
          <span className="sr-only">exclui </span>
          {step.excluded_ha > 0 ? '−' : ''}
          {formatHa(step.excluded_ha)} ha
        </span>
      </div>
      <div className="pl-10">
        <Bar fraction={step.excluded_ha / total} />
        <p className="mt-1 text-xs text-muted-foreground">{step.why}</p>
      </div>
    </li>
  )
}

function Bar({ fraction, highlight = false }: { fraction: number; highlight?: boolean }) {
  return (
    <div className="mt-1 h-1.5 rounded-sm bg-muted/60" aria-hidden>
      <div
        className={`h-full rounded-sm ${highlight ? 'bg-cherry' : 'bg-muted-foreground/45'}`}
        style={{ width: `${Math.min(fraction, 1) * 100}%` }}
      />
    </div>
  )
}

function Limitations({ items }: { items: string[] }) {
  return (
    <section aria-labelledby="limits-title">
      <h2 id="limits-title" className="font-heading text-xl font-[620] tracking-tight [font-stretch:80%]">
        Limitações
      </h2>
      <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm text-muted-foreground marker:text-border">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  )
}

function References({ rationale }: { rationale: Rationale }) {
  return (
    <section aria-labelledby="refs-title" className="border-t border-border pt-4">
      <h2 id="refs-title" className="font-mono text-[11px] tracking-wide text-muted-foreground uppercase">
        Referências
      </h2>
      <ul className="mt-2 space-y-2 text-xs text-muted-foreground">
        {rationale.references.map((ref) => (
          <li key={ref.key}>
            {ref.citation}{' '}
            <a className="text-foreground underline-offset-2 hover:underline" href={`https://doi.org/${ref.doi}`} target="_blank" rel="noreferrer">
              doi:{ref.doi}
            </a>
            <span className="block">Usado para: {ref.used_for}.</span>
          </li>
        ))}
      </ul>
      <p className="mt-3 font-mono text-[11px] text-muted-foreground">Método {rationale.method_version}</p>
    </section>
  )
}
