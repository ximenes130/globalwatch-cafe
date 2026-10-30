import { useQueryClient } from '@tanstack/react-query'
import { ArrowUp, RotateCw } from 'lucide-react'
import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from 'react'
import { ChatCards, type ShowPolygon } from '@/components/ChatCards'
import { Button } from '@/components/ui/button'
import { UsageNote } from '@/components/UsageNote'
import { type ChatCard, type ChatTurn, getChatHistory, sendChat } from '@/lib/api'
import { renderMarkdown } from '@/lib/markdown'
import { prefersReducedMotion } from '@/lib/motion'
import { usageKey } from '@/lib/query'
import { useQuota } from '@/lib/usage'

const MAX_MESSAGE = 1000
// Limites do backend: 10 mensagens de até 4.000 caracteres vão ao modelo.
const HISTORY_SENT = 10
const HISTORY_CHARS = 4000

const SUGGESTIONS = ['Por que tanta área ficou de fora?', 'Qual a confiança deste resultado?', 'Fale do polígono 1.']
const SECOND_DATE_SUGGESTION = 'O que a segunda data mudou no resultado?'

type Props = { analysisId: string; hasSecondDate: boolean; onShowPolygon: ShowPolygon }

type ChatEntry = {
  id: string
  role: 'user' | 'assistant'
  content: string
  cards?: ChatCard[]
  /** Pergunta que não teve resposta: mensagem do backend, mostrada com "Tentar de novo". Não é gravada. */
  error?: string
}

/**
 * Conversa sobre a análise (R5.1, R5.7, R5.8). Na primeira abertura pede a apresentação;
 * cada resposta traz os cards do que o assistente consultou (R5.14).
 */
export function Chat({ analysisId, hasSecondDate, onShowPolygon }: Props) {
  // `null` enquanto a conversa gravada carrega (T5.5).
  const [stored, setEntries] = useState<ChatEntry[] | null>(null)
  const entries = stored ?? []
  const [loadError, setLoadError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)
  const [introError, setIntroError] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const end = useRef<HTMLDivElement>(null)
  const lastAnswer = useRef<HTMLLIElement>(null)
  const started = useRef(false)
  const queryClient = useQueryClient()
  // Sem mensagens hoje, o campo e as sugestões param e o rodapé diz quando libera (R6.17).
  const blocked = useQuota('messages')?.blocked ?? false

  useEffect(() => {
    const behavior = prefersReducedMotion() ? 'auto' : 'smooth'
    // Resposta nova abre pelo começo (cards e depois o texto); o resto rola até o fim.
    if (!pending && stored?.at(-1)?.role === 'assistant') lastAnswer.current?.scrollIntoView({ block: 'start', behavior })
    else end.current?.scrollIntoView({ block: 'end', behavior })
  }, [stored, pending])

  async function ask(message: string | null, before: ChatEntry[]) {
    setPending(true)
    try {
      const answer = await sendChat(analysisId, message, historyOf(before))
      setEntries((current) => [
        ...(current ?? []),
        { id: crypto.randomUUID(), role: 'assistant', content: answer.reply, cards: answer.cards },
      ])
      return null
    } catch (error) {
      return error instanceof Error ? error.message : 'O assistente não respondeu.'
    } finally {
      setPending(false)
      // Resposta, erro ou 429: a cota mostrada acompanha o backend.
      void queryClient.invalidateQueries({ queryKey: usageKey })
    }
  }

  async function intro() {
    setIntroError(null)
    setIntroError(await ask(null, []))
  }

  async function load() {
    setLoadError(null)
    try {
      const saved = await getChatHistory(analysisId)
      setEntries(saved.map(({ id, role, content, cards }) => ({ id: String(id), role, content, cards })))
      // Apresentação só numa conversa vazia.
      if (saved.length === 0) await intro()
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : 'Não foi possível carregar a conversa.')
    }
  }

  useEffect(() => {
    // Uma vez por montagem (o modo estrito roda o efeito duas vezes).
    if (started.current) return
    started.current = true
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function send(text: string) {
    const message = text.trim()
    // Antes de a conversa gravada chegar, o histórico enviado estaria incompleto.
    if (!message || pending || blocked || stored === null) return
    const question: ChatEntry = { id: crypto.randomUUID(), role: 'user', content: message }
    const before = entries
    setEntries([...before, question])
    setDraft('')
    const error = await ask(message, before)
    if (error) setEntries((current) => (current ?? []).map((e) => (e.id === question.id ? { ...e, error } : e)))
  }

  async function retry(entry: ChatEntry) {
    const index = entries.findIndex((e) => e.id === entry.id)
    const before = entries.slice(0, index)
    // A pergunta volta ao fim, sem o erro: a nova resposta vem logo depois dela.
    const question = { ...entry, error: undefined }
    setEntries([...before, ...entries.slice(index + 1), question])
    const error = await ask(entry.content, before)
    if (error) setEntries((current) => (current ?? []).map((e) => (e.id === question.id ? { ...e, error } : e)))
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    void send(draft)
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter envia; Shift+Enter quebra a linha. Durante a composição (acentos em IME), não.
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      void send(draft)
    }
  }

  const asked = entries.some((e) => e.role === 'user')
  const suggestions = hasSecondDate ? [...SUGGESTIONS, SECOND_DATE_SUGGESTION] : SUGGESTIONS

  return (
    <div className="flex min-h-full flex-col">
      <ol className="flex-1 space-y-5 p-4 sm:p-6" aria-live="polite" aria-relevant="additions" aria-label="Conversa com o assistente">
        {entries.map((entry, i) =>
          entry.role === 'user' ? (
            <li key={entry.id} className="flex flex-col items-end gap-1.5 duration-(--duration-base) animate-in fade-in slide-in-from-bottom-1">
              <p className="max-w-[85%] rounded-lg bg-muted px-3 py-2 text-sm whitespace-pre-wrap">{entry.content}</p>
              {entry.error && (
                <div role="alert" className="flex max-w-[85%] flex-wrap items-center justify-end gap-2 text-xs text-destructive">
                  <span>{entry.error}</span>
                  <Button size="xs" variant="outline" onClick={() => void retry(entry)} disabled={pending}>
                    <RotateCw /> Tentar de novo
                  </Button>
                </div>
              )}
            </li>
          ) : (
            <li
              key={entry.id}
              ref={i === entries.length - 1 ? lastAnswer : undefined}
              className="scroll-mt-14 space-y-3 duration-(--duration-slow) animate-in fade-in slide-in-from-bottom-1"
            >
              <ChatCards cards={entry.cards ?? []} onShowPolygon={onShowPolygon} />
              <div className="space-y-2.5 text-sm leading-relaxed">{renderMarkdown(entry.content)}</div>
            </li>
          ),
        )}
        {stored === null && !loadError && (
          <li role="status" className="py-1 text-sm text-muted-foreground">
            Carregando a conversa…
          </li>
        )}
        {loadError && (
          <li role="alert" className="space-y-2 rounded-lg border border-border bg-card p-3 text-sm">
            <p>{loadError}</p>
            <Button size="sm" variant="outline" onClick={() => void load()}>
              <RotateCw /> Tentar de novo
            </Button>
          </li>
        )}
        {pending && (
          <li role="status" className="flex items-center gap-1 py-1" aria-label="O assistente está escrevendo">
            {[0, 1, 2].map((dot) => (
              <span
                key={dot}
                className="size-1.5 animate-pulse rounded-full bg-muted-foreground/60"
                style={{ animationDelay: `${dot * 160}ms` }}
              />
            ))}
          </li>
        )}
        {introError && (
          <li role="alert" className="space-y-2 rounded-lg border border-border bg-card p-3 text-sm">
            <p>{introError}</p>
            <Button size="sm" variant="outline" onClick={() => void intro()} disabled={pending}>
              <RotateCw /> Tentar de novo
            </Button>
          </li>
        )}
      </ol>
      <div ref={end} />

      <div className="sticky bottom-0 border-t border-border bg-background p-4 sm:px-6">
        {!asked && entries.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-2" aria-label="Sugestões de perguntas">
            {suggestions.map((text) => (
              <Button key={text} size="sm" variant="outline" className="h-auto py-1 whitespace-normal" disabled={pending || blocked} onClick={() => void send(text)}>
                {text}
              </Button>
            ))}
          </div>
        )}
        <form onSubmit={onSubmit} className="flex items-end gap-2">
          <label htmlFor="chat-message" className="sr-only">
            Pergunta sobre a análise
          </label>
          <textarea
            id="chat-message"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={onKeyDown}
            maxLength={MAX_MESSAGE}
            disabled={blocked}
            rows={2}
            placeholder="Pergunte sobre áreas, polígonos ou limitações"
            className="min-h-10 flex-1 resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-50"
          />
          <Button type="submit" size="icon-lg" disabled={pending || blocked || stored === null || !draft.trim()} aria-label="Enviar pergunta">
            <ArrowUp />
          </Button>
        </form>
        <UsageNote kind="messages" className="mt-2" />
        <p className="mt-1 flex justify-between gap-2 text-[11px] text-muted-foreground">
          <span>Respostas geradas por IA a partir dos dados do processamento.</span>
          {draft.length > MAX_MESSAGE * 0.8 && (
            <span className="font-mono tabular-nums">
              {draft.length}/{MAX_MESSAGE}
            </span>
          )}
        </p>
      </div>
    </div>
  )
}

/** Só o texto das mensagens que deram certo, as últimas 10, cortadas no limite da API. */
function historyOf(entries: ChatEntry[]): ChatTurn[] {
  return entries
    .filter((entry) => !entry.error)
    .slice(-HISTORY_SENT)
    .map(({ role, content }) => ({ role, content: content.slice(0, HISTORY_CHARS) }))
}
