// Validação no cliente (R4.3). O backend valida de novo: isto só poupa um envio inútil.

// Espelha `max_upload_mb` de backend/app/config.py.
export const MAX_UPLOAD_MB = 20

const sizeFormat = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 })

export const formatSize = (bytes: number) =>
  bytes < 1024 * 1024
    ? `${sizeFormat.format(Math.max(bytes / 1024, 1))} KB`
    : `${sizeFormat.format(bytes / 1024 / 1024)} MB`

/** Motivo da recusa, ou `null` se o arquivo pode ser enviado. */
export function rejectReason(file: File): string | null {
  if (!/\.tiff?$/i.test(file.name)) return `“${file.name}” não é GeoTIFF: envie um arquivo .tif ou .tiff.`
  if (file.size === 0) return `“${file.name}” está vazio.`
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
    return `“${file.name}” tem ${formatSize(file.size)}; o limite é ${MAX_UPLOAD_MB} MB.`
  }
  return null
}

/** Separa a SCL da imagem quando os dois arquivos chegam juntos, pelo nome. */
export function splitDropped(files: File[]): { image?: File; scl?: File } {
  if (files.length < 2) return files[0] ? { image: files[0] } : {}
  const scl = files.find((file) => /scl/i.test(file.name))
  const image = files.find((file) => file !== scl)
  return scl ? { image, scl } : { image }
}
