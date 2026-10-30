// Faixa de NDVI marcada como candidata. Espelha `ndvi_min`/`ndvi_max` de
// backend/app/processing/params.py; atualizar junto na calibração (T2.5).
export const CANDIDATE_NDVI = { min: 0.55, max: 0.72 } as const

export const NDVI_SCALE = { min: -0.2, max: 1 } as const

// Amplitude de NDVI entre duas datas que tira o pixel da área potencial.
// Espelha `ndvi_amplitude_max` de backend/app/processing/params.py (T3.5).
export const NDVI_AMPLITUDE_MAX = 0.25
