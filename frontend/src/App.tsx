import { useSession } from '@/lib/use-session'
import { Home } from '@/pages/Home'
import { Login } from '@/pages/Login'

export default function App() {
  const session = useSession()

  // Evita piscar a tela de login enquanto a sessão salva é lida.
  if (session === undefined) return null

  return session ? <Home session={session} /> : <Login />
}
