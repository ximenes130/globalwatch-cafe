import { supabase } from '@/lib/supabase'

const API_URL = import.meta.env.VITE_API_URL

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

/** Chama o backend com o JWT da sessão. Um 401 encerra a sessão e volta ao login. */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { data } = await supabase.auth.getSession()
  const headers = new Headers(init.headers)
  if (data.session) headers.set('Authorization', `Bearer ${data.session.access_token}`)

  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, { ...init, headers })
  } catch {
    throw new ApiError(0, 'Não foi possível falar com o servidor. Verifique a conexão e tente de novo.')
  }

  if (response.status === 401) {
    await supabase.auth.signOut()
    throw new ApiError(401, 'Sua sessão expirou. Entre novamente.')
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(response.status, body?.detail ?? `O servidor respondeu ${response.status}.`)
  }
  return response.json() as Promise<T>
}

export type Me = { user_id: string; email: string | null }

export const getMe = () => apiFetch<Me>('/me')
