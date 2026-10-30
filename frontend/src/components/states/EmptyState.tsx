import type { ReactNode } from 'react'

type Props = { title: string; children?: ReactNode; illustration?: ReactNode }

/** Ausência de dados como convite para agir, não como erro. */
export function EmptyState({ title, children, illustration }: Props) {
  return (
    <div className="rounded-lg border border-dashed border-border px-5 py-8 sm:px-8">
      {illustration}
      <p className="font-heading text-2xl font-[620] tracking-tight [font-stretch:80%]">{title}</p>
      {children && <div className="mt-2 max-w-prose text-sm text-muted-foreground">{children}</div>}
    </div>
  )
}
