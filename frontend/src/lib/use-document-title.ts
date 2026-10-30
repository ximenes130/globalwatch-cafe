import { useEffect } from 'react'

const APP = 'Global Watch'

/** Título da aba por tela, para quem tem várias abertas. */
export function useDocumentTitle(title: string | null) {
  useEffect(() => {
    document.title = title ? `${title} · ${APP}` : `${APP} · áreas potenciais de café`
  }, [title])
}
