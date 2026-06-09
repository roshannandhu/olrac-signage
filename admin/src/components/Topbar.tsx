import { useLocation } from 'react-router-dom'

const titles: Record<string, string> = {
  '/': 'Dashboard',
  '/content': 'Content Library',
  '/screens': 'Screens',
  '/playlist': 'Playlist Editor',
  '/groups': 'Screen Groups',
  '/websites': 'Websites',
  '/reports': 'Playback Report',
  '/activity': 'Activity Log',
  '/alerts': 'Alerts',
}

export default function Topbar() {
  const { pathname } = useLocation()
  const title = titles[pathname] ?? 'Dashboard'

  return (
    <header className="topbar">
      <span className="tb-title">{title}</span>
      <div className="sbox">
        <svg width="12" height="12" viewBox="0 0 20 20" fill="var(--text3)">
          <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
        </svg>
        <input type="text" placeholder="Search…" />
      </div>
      <div className="ico-btn">🌙</div>
      <div className="ico-btn">
        <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
          <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z" />
        </svg>
      </div>
    </header>
  )
}
