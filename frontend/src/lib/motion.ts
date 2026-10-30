// Tokens de movimento (spec 004, R4.18). Espelham as variáveis de index.css,
// porque o MapLibre anima em JavaScript e não lê CSS.
export const DURATION = { fast: 120, base: 200, slow: 320 } as const

/** Voo do mapa até a imagem quando o resultado chega (R4.19). */
export const FLY_MS = 800

/** Curva de entrada `cubic-bezier(0.2, 0, 0, 1)`, aproximada por cúbica para o MapLibre. */
export const easeOut = (t: number) => 1 - (1 - t) ** 3

const query = typeof window === 'undefined' ? null : window.matchMedia('(prefers-reduced-motion: reduce)')

/**
 * Lido na hora de animar, não em cache: a preferência do sistema pode mudar com a
 * página aberta (R4.20). A regra de index.css cobre o CSS; isto cobre o mapa.
 */
export const prefersReducedMotion = () => query?.matches ?? false
