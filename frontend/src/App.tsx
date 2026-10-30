import type { Session } from '@supabase/supabase-js'
import { Outlet, Route, Routes } from 'react-router'
import { AppHeader } from '@/components/AppHeader'
import { ServerWaking } from '@/components/states/ServerWaking'
import { useSession } from '@/lib/use-session'
import { Analyses } from '@/pages/Analyses'
import { Analysis } from '@/pages/Analysis'
import { Login } from '@/pages/Login'
import { NotFound } from '@/pages/NotFound'

export default function App() {
  const session = useSession()

  // Evita piscar a tela de login enquanto a sessão salva é lida.
  if (session === undefined) return null
  if (!session) return <Login />

  return (
    <Routes>
      <Route element={<Layout session={session} />}>
        <Route index element={<Analyses />} />
        <Route path="analyses/:id" element={<Analysis />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}

function Layout({ session }: { session: Session }) {
  return (
    <div className="flex min-h-dvh flex-col">
      <ServerWaking />
      <AppHeader email={session.user.email} />
      <Outlet />
    </div>
  )
}
