import type { ChatCard } from '@/lib/api'

export type ChatEntry = {
  id: string
  role: 'user' | 'assistant'
  content: string
  cards?: ChatCard[]
  /** Pergunta que não teve resposta: mensagem do backend, mostrada com "Tentar de novo". */
  error?: string
}

// Até a T5.5 (histórico no banco) a conversa vive na sessão do navegador, por análise.
const key = (analysisId: string) => `chat:${analysisId}`

export function loadChat(analysisId: string): ChatEntry[] {
  try {
    const raw = sessionStorage.getItem(key(analysisId))
    return raw ? (JSON.parse(raw) as ChatEntry[]) : []
  } catch {
    // Armazenamento bloqueado ou conteúdo inválido: começa do zero.
    return []
  }
}

export function saveChat(analysisId: string, entries: ChatEntry[]) {
  try {
    sessionStorage.setItem(key(analysisId), JSON.stringify(entries))
  } catch {
    // Sem armazenamento a conversa só não sobrevive ao recarregar.
  }
}

export function forgetChat(analysisId: string) {
  try {
    sessionStorage.removeItem(key(analysisId))
  } catch {
    // Idem.
  }
}
