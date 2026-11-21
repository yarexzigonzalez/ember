import { Navigate, Route, Routes } from 'react-router-dom'

import { RequireAuth } from '@/components/RequireAuth'
import { Shell } from '@/components/Shell'
import { DemoEntry } from '@/pages/DemoEntry'
import { Landing } from '@/pages/Landing'
import { Login } from '@/pages/Login'
import { Pipeline } from '@/pages/Pipeline'
import { Signup } from '@/pages/Signup'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/demo" element={<DemoEntry />} />
      <Route
        path="/app"
        element={
          <RequireAuth>
            <Shell>
              <Pipeline />
            </Shell>
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
