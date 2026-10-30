import { Fragment, type ReactNode } from 'react'

/**
 * Markdown simples das respostas do assistente (R5.8): parágrafos, listas, negrito e
 * itálico. Monta elementos React a partir do texto; nada vira HTML, então o que o
 * modelo escrever aparece como texto.
 */
export function renderMarkdown(text: string): ReactNode {
  const blocks: ReactNode[] = []
  let paragraph: string[] = []
  let list: { ordered: boolean; items: string[] } | null = null

  const flush = () => {
    if (paragraph.length) {
      blocks.push(<p key={blocks.length}>{inline(paragraph.join(' '))}</p>)
      paragraph = []
    }
    if (list) {
      const items = list.items.map((item, i) => <li key={i}>{inline(item)}</li>)
      blocks.push(
        list.ordered ? (
          <ol key={blocks.length} className="list-decimal space-y-1 pl-5">{items}</ol>
        ) : (
          <ul key={blocks.length} className="list-disc space-y-1 pl-5 marker:text-muted-foreground">{items}</ul>
        ),
      )
      list = null
    }
  }

  for (const raw of text.split('\n')) {
    const line = raw.trim()
    const bullet = /^[-*•]\s+(.*)$/.exec(line)
    const numbered = /^\d+[.)]\s+(.*)$/.exec(line)
    if (!line) {
      flush()
    } else if (bullet || numbered) {
      const ordered = Boolean(numbered)
      if (paragraph.length || (list && list.ordered !== ordered)) flush()
      list ??= { ordered, items: [] }
      list.items.push((bullet ?? numbered)![1])
    } else {
      if (list) flush()
      // Títulos não são pedidos ao modelo; se vierem, viram texto comum.
      paragraph.push(line.replace(/^#{1,6}\s+/, ''))
    }
  }
  flush()
  return blocks
}

/** `**negrito**` e `*itálico*`/`_itálico_`; o resto é texto. */
function inline(text: string): ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|_[^_\s][^_]*_)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return <strong key={i} className="font-semibold">{part.slice(2, -2)}</strong>
    }
    if (part.length > 2 && ((part.startsWith('*') && part.endsWith('*')) || (part.startsWith('_') && part.endsWith('_')))) {
      return <em key={i}>{part.slice(1, -1)}</em>
    }
    return <Fragment key={i}>{part}</Fragment>
  })
}
