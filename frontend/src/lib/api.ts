import { supabase } from '@/lib/supabase'
import { trackSlow } from '@/lib/server-waking'

const API_URL = import.meta.env.VITE_API_URL

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

const OFFLINE_MESSAGE = 'Não foi possível falar com o servidor. Verifique a conexão e tente de novo.'

async function authorization(): Promise<string | null> {
  const { data } = await supabase.auth.getSession()
  return data.session ? `Bearer ${data.session.access_token}` : null
}

/** Um 401 encerra a sessão e volta ao login; outros erros usam o `detail` do backend. */
async function errorFrom(status: number, body: { detail?: unknown } | null): Promise<ApiError> {
  if (status === 401) {
    await supabase.auth.signOut()
    return new ApiError(401, 'Sua sessão expirou. Entre novamente.')
  }
  const detail = typeof body?.detail === 'string' ? body.detail : null
  return new ApiError(status, detail ?? `O servidor respondeu ${status}.`)
}

/** Chama o backend com o JWT da sessão. */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const auth = await authorization()
  if (auth) headers.set('Authorization', auth)

  let response: Response
  try {
    response = await trackSlow(fetch(`${API_URL}${path}`, { ...init, headers }))
  } catch {
    throw new ApiError(0, OFFLINE_MESSAGE)
  }

  if (!response.ok) {
    throw await errorFrom(response.status, await response.json().catch(() => null))
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export type Me = { user_id: string; email: string | null }

export const getMe = () => apiFetch<Me>('/me')

export type AnalysisStatus = 'processing' | 'completed' | 'failed'

export type AnalysisListItem = {
  id: string
  filename: string
  created_at: string
  status: AnalysisStatus
  acquired_at: string | null
  potential_area_ha: number | null
}

/** Nomes dos níveis de exclusão, na ordem da cascata (backend/app/processing/classification.py). */
export type ExclusionLevel =
  | 'no_data'
  | 'quality_mask'
  | 'low_vegetation'
  | 'dense_canopy'
  | 'low_chlorophyll'
  | 'high_amplitude'
  | 'small_patch'

export type IndexStats = { min: number; p5: number; median: number; p95: number; max: number }

export type Stats = {
  total_area_ha: number
  valid_area_ha: number
  masked_area_ha: number
  potential_area_ha: number
  polygon_count: number
  ndvi: IndexStats
  gndvi: IndexStats | null
  excluded_area_ha: Record<ExclusionLevel, number>
  second_acquired_at: string | null
}

export type RationaleStep = {
  level: string
  name: ExclusionLevel
  rule: string
  threshold: number | null
  excluded_ha: number
  why: string
  references: string[]
}

export type Reference = { key: string; citation: string; doi: string; used_for: string }

export type Rationale = {
  method_version: string
  summary: string
  steps: RationaleStep[]
  limitations: string[]
  references: Reference[]
}

export type ResultUrls = {
  rgb_png: string
  classification_png: string
  polygons_png: string
  geojson: string
}

/** Cantos em WGS84 (lon, lat): superior-esquerdo, superior-direito, inferior-direito, inferior-esquerdo. */
export type Corners = [[number, number], [number, number], [number, number], [number, number]]

export type Analysis = {
  id: string
  status: AnalysisStatus
  filename: string
  created_at: string
  acquired_at: string | null
  crs: string | null
  bounds_wgs84: Corners | null
  stats: Stats | null
  method_version: string | null
  rationale: Rationale | null
  error: string | null
  urls: ResultUrls | null
}

export const listAnalyses = () => apiFetch<AnalysisListItem[]>('/analyses')

export const getAnalysis = (id: string) => apiFetch<Analysis>(`/analyses/${id}`)

export type UploadFiles = {
  image: File
  scl: File | null
  image2: File | null
  scl2: File | null
}

/**
 * `POST /analyses` por `XMLHttpRequest`: `fetch` não informa o progresso do envio (R4.4).
 * O aviso de servidor acordando só conta depois que o arquivo terminou de subir.
 */
export async function createAnalysis(
  files: UploadFiles,
  onProgress: (fraction: number) => void,
): Promise<{ id: string; status: AnalysisStatus }> {
  const form = new FormData()
  form.append('image', files.image)
  if (files.scl) form.append('scl', files.scl)
  if (files.image2) form.append('image_2', files.image2)
  if (files.scl2) form.append('scl_2', files.scl2)
  const auth = await authorization()

  const xhr = new XMLHttpRequest()
  const done = new Promise<void>((resolve, reject) => {
    xhr.onload = () => resolve()
    xhr.onerror = () => reject(new ApiError(0, OFFLINE_MESSAGE))
  })
  xhr.upload.onprogress = (event) => {
    if (event.lengthComputable) onProgress(event.loaded / event.total)
  }
  xhr.upload.onload = () => {
    onProgress(1)
    trackSlow(done).catch(() => {})
  }
  xhr.open('POST', `${API_URL}/analyses`)
  if (auth) xhr.setRequestHeader('Authorization', auth)
  xhr.responseType = 'json'
  xhr.send(form)

  await done
  if (xhr.status < 200 || xhr.status >= 300) throw await errorFrom(xhr.status, xhr.response)
  return xhr.response
}

export const deleteAnalysis = (id: string) =>
  apiFetch<void>(`/analyses/${id}`, { method: 'DELETE' })

/** Card de uma resposta do chat: o mesmo objeto que a ferramenta entregou ao modelo (spec 005). */
export type SummaryCard = {
  kind: 'summary'
  data: {
    filename: string
    acquired_at: string | null
    second_acquired_at: string | null
    total_area_ha: number
    valid_area_ha: number
    masked_area_ha: number
    potential_area_ha: number
    polygon_count: number
    excluded_area_ha: Partial<Record<ExclusionLevel, number>>
    thresholds: { ndvi_min: number; ndvi_max: number; min_area_ha: number; ndvi_amplitude_max?: number }
    method_version: string
  }
}

export type PolygonCard = {
  kind: 'polygon'
  data: { id: number; area_ha: number; ndvi_mean: number; gndvi_mean: number | null; centroid: [number, number] }
}

export type LimitationsCard = {
  kind: 'limitations'
  data: { items: string[]; references: { citation: string; doi: string }[] }
}

export type ChatCard = SummaryCard | PolygonCard | LimitationsCard

export type ChatTurn = { role: 'user' | 'assistant'; content: string }

export type ChatAnswer = { reply: string; cards: ChatCard[] }

/** `message: null` pede a apresentação (só com histórico vazio). */
export const sendChat = (id: string, message: string | null, history: ChatTurn[]) =>
  apiFetch<ChatAnswer>(`/analyses/${id}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history }),
  })

/** Mensagem gravada da conversa (T5.5), com os cards da resposta. */
export type ChatMessage = { id: number; role: 'user' | 'assistant'; content: string; cards: ChatCard[]; created_at: string }

export const getChatHistory = (id: string) => apiFetch<ChatMessage[]>(`/analyses/${id}/chat`)

/** Cota de hoje e retenção (R6.16 a R6.19): números do backend, nunca calculados aqui. */
export type Usage = {
  uploads: { used: number; limit: number }
  messages: { used: number; limit: number }
  resets_at: string
  retention_days: number
}

export const getUsage = () => apiFetch<Usage>('/me/usage')
