// Números e datas em pt-BR. Valores vêm prontos da API (C2); aqui só a apresentação.

const hectares = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const percent = new Intl.NumberFormat('pt-BR', { style: 'percent', minimumFractionDigits: 1, maximumFractionDigits: 1 })
const index = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 4 })

export const formatHa = (value: number) => hectares.format(value)
export const formatPercent = (part: number, total: number) => percent.format(total > 0 ? part / total : 0)
export const formatIndex = (value: number) => index.format(value)

// A data da imagem é a da passagem do satélite: mostrada em UTC, como nos metadados da cena.
const imageDate = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium', timeZone: 'UTC' })
const localDateTime = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' })

export const formatImageDate = (iso: string) => imageDate.format(new Date(iso))
export const formatDateTime = (iso: string) => localDateTime.format(new Date(iso))

/** "2 min 05 s" a partir de segundos inteiros. */
export function formatElapsed(seconds: number) {
  const minutes = Math.floor(seconds / 60)
  const rest = String(seconds % 60).padStart(2, '0')
  return minutes > 0 ? `${minutes} min ${rest} s` : `${seconds} s`
}
