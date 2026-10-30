import { useSyncExternalStore } from 'react'

// O Render free dorme sem uso e leva até um minuto para acordar (R4.13). Uma
// requisição sem resposta depois de 5 s conta como "servidor acordando".
const SLOW_AFTER_MS = 5000

let slowRequests = 0
const listeners = new Set<() => void>()

function emit() {
  for (const listener of listeners) listener()
}

/** Conta a requisição como lenta se ela passar de 5 s, até ela terminar. */
export function trackSlow<T>(request: Promise<T>): Promise<T> {
  let counted = false
  const timer = setTimeout(() => {
    counted = true
    slowRequests += 1
    emit()
  }, SLOW_AFTER_MS)
  return request.finally(() => {
    clearTimeout(timer)
    if (counted) {
      slowRequests -= 1
      emit()
    }
  })
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export function useServerWaking(): boolean {
  return useSyncExternalStore(subscribe, () => slowRequests > 0)
}
