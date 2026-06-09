import { useLocation, useNavigate } from 'react-router-dom'
import type { ReactNode } from 'react'

interface NavItem {
  to: string
  label: string
  icon: ReactNode
  badge?: number
  match?: string[] // extra paths that also activate this item
}

const icoDashboard = (
  <svg className="ni-ico" viewBox="0 0 20 20" fill="currentColor"><path d="M3 4a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H4a1 1 0 01-1-1V4zm0 8a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H4a1 1 0 01-1-1v-4zm8-8a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1V4zm0 8a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" /></svg>
)
const icoContent = (
  <svg className="ni-ico" viewBox="0 0 20 20" fill="currentColor"><path d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" /></svg>
)
const icoScreens = (
  <svg className="ni-ico" viewBox="0 0 20 20" fill="currentColor"><path d="M2 6a2 2 0 012-2h12a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6zm2 2v4h12V8H4z" /></svg>
)
const icoGroups = (
  <svg className="ni-ico" viewBox="0 0 20 20" fill="currentColor"><path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM14 11a1 1 0 011 1v1h1a1 1 0 110 2h-1v1a1 1 0 11-2 0v-1h-1a1 1 0 110-2h1v-1a1 1 0 011-1z" /></svg>
)
const icoWebsites = (
  <svg className="ni-ico" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4.083 9h1.946c.089-1.546.383-2.97.837-4.118A6.004 6.004 0 004.083 9zM10 2a8 8 0 100 16A8 8 0 0010 2zm0 2c-.076 0-.232.032-.465.262-.238.234-.497.623-.737 1.182-.389.907-.673 2.142-.766 3.556h3.936c-.093-1.414-.377-2.649-.766-3.556-.24-.56-.5-.948-.737-1.182C10.232 4.032 10.076 4 10 4zm3.971 5c-.089-1.546-.383-2.97-.837-4.118A6.004 6.004 0 0115.917 9h-1.946zm-2.003 2H8.032c.093 1.414.377 2.649.766 3.556.24.56.5.948.737 1.182.233.23.389.262.465.262.076 0 .232-.032.465-.262.238-.234.498-.623.737-1.182.389-.907.673-2.142.766-3.556zm1.166 4.118c.454-1.147.748-2.572.837-4.118h1.946a6.004 6.004 0 01-2.783 4.118zm-6.268 0C6.412 13.97 6.118 12.546 6.03 11H4.083a6.004 6.004 0 002.783 4.118z" clipRule="evenodd" /></svg>
)
const icoReports = (
  <svg className="ni-ico" viewBox="0 0 20 20" fill="currentColor"><path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zm6-4a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zm6-3a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" /></svg>
)
const icoActivity = (
  <svg className="ni-ico" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" /></svg>
)
const icoAlerts = (
  <svg className="ni-ico" viewBox="0 0 20 20" fill="currentColor"><path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z" /></svg>
)

const mainItems: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: icoDashboard },
  { to: '/content', label: 'Content', icon: icoContent },
  { to: '/screens', label: 'Screens', icon: icoScreens, match: ['/playlist'] },
  { to: '/groups', label: 'Groups', icon: icoGroups },
  { to: '/websites', label: 'Websites', icon: icoWebsites },
]
const adminItems: NavItem[] = [
  { to: '/reports', label: 'Reports', icon: icoReports },
  { to: '/activity', label: 'Activity Log', icon: icoActivity },
  { to: '/alerts', label: 'Alerts', icon: icoAlerts, badge: 2 },
]

export default function Sidebar() {
  const { pathname } = useLocation()
  const nav = useNavigate()

  const isActive = (item: NavItem) =>
    pathname === item.to || (item.match?.some((m) => pathname.startsWith(m)) ?? false)

  const renderItem = (item: NavItem) => (
    <div
      key={item.to}
      className={`ni${isActive(item) ? ' active' : ''}`}
      onClick={() => nav(item.to)}
    >
      {item.icon}
      <span>{item.label}</span>
      {item.badge ? <span className="nbadge">{item.badge}</span> : null}
    </div>
  )

  return (
    <aside className="sb">
      <div className="sb-logo">
        <div className="sb-badge">
          <div className="sb-icon">📺</div>
          <span className="sb-name">Olrac</span>
        </div>
        <div className="sb-sub">Signage Platform</div>
      </div>
      <nav className="nav">
        <div className="nav-lbl">Main</div>
        {mainItems.map(renderItem)}
        <div className="nav-lbl">Admin</div>
        {adminItems.map(renderItem)}
      </nav>
      <div className="sb-foot">
        <div className="u-chip">
          <div className="av">R</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--text)' }}>Admin</div>
            <div style={{ fontSize: 10.5, color: 'var(--text3)' }}>Super Admin</div>
          </div>
        </div>
      </div>
    </aside>
  )
}
