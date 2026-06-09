import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useStore } from './store'
import Sidebar from './components/Sidebar'
import Topbar from './components/Topbar'
import ToastHost from './components/ToastHost'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Content from './pages/Content'
import Screens from './pages/Screens'
import PlaylistEditor from './pages/PlaylistEditor'
import Groups from './pages/Groups'
import Websites from './pages/Websites'
import Reports from './pages/Reports'
import Activity from './pages/Activity'
import Alerts from './pages/Alerts'

function Shell() {
  return (
    <div className="app">
      <Sidebar />
      <main className="main">
        <Topbar />
        <div className="cnt">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

function Protected({ children }: { children: ReactNode }) {
  const authed = useStore((s) => s.authed)
  return authed ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          element={
            <Protected>
              <Shell />
            </Protected>
          }
        >
          <Route path="/" element={<Dashboard />} />
          <Route path="/content" element={<Content />} />
          <Route path="/screens" element={<Screens />} />
          <Route path="/playlist" element={<PlaylistEditor />} />
          <Route path="/groups" element={<Groups />} />
          <Route path="/websites" element={<Websites />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/activity" element={<Activity />} />
          <Route path="/alerts" element={<Alerts />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <ToastHost />
    </>
  )
}
