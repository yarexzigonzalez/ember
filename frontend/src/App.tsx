import { Navigate, Outlet, Route, Routes } from 'react-router-dom'

import { RequireAuth } from '@/components/RequireAuth'
import { Shell } from '@/components/Shell'
import { DemoEntry } from '@/pages/DemoEntry'
import { Ghost } from '@/pages/Ghost'
import { Landing } from '@/pages/Landing'
import { Login } from '@/pages/Login'
import { Pipeline } from '@/pages/Pipeline'
import { Settings } from '@/pages/Settings'
import { Signup } from '@/pages/Signup'

function AppLayout() {
  return (
    <RequireAuth>
      <Shell>
        <Outlet />
      </Shell>
    </RequireAuth>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/demo" element={<DemoEntry />} />
      <Route path="/app" element={<AppLayout />}>
        <Route index element={<Pipeline />} />
        <Route path="ghost" element={<Ghost />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
