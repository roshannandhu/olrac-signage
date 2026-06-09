import { useNavigate } from 'react-router-dom'
import type { Screen } from '../types'
import { useStore } from '../store'

export default function ScreenCard({ s, onSettings }: { s: Screen; onSettings?: (screen: Screen) => void }) {
  const nav = useNavigate()
  const selectScreen = useStore((st) => st.selectScreen)
  const offline = s.status === 'offline'

  const openPlaylist = () => {
    selectScreen(s.name)
    nav('/playlist')
  }

  return (
    <div className="scc" onClick={openPlaylist}>
      <div className="sth">
        <div className="sprev" style={offline ? { color: 'rgba(255,255,255,.15)' } : undefined}>
          {offline ? 'Offline' : s.name}
        </div>
        <span className={`sstat ${offline ? 'off' : 'on'}`}>● {offline ? 'Offline' : 'Online'}</span>
      </div>
      <div className="sinf">
        <div className="snm">{s.name}</div>
        <div className="smt">{s.lastSeen} · {s.orientLabel} · {s.deg}°</div>
        <div className="sac" onClick={(e) => e.stopPropagation()}>
          <button className={`btn btn-sm ${offline ? 'btn-g' : 'btn-p'}`} onClick={openPlaylist}>Edit Playlist</button>
          <button className="btn btn-g btn-sm" onClick={() => onSettings?.(s)}>Settings</button>
        </div>
      </div>
    </div>
  )
}
