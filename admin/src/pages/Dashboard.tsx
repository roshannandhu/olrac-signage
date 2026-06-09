import { useNavigate } from 'react-router-dom'
import type { Screen } from '../types'
import MediaCard from '../components/MediaCard'
import ScreenCard from '../components/ScreenCard'
import { useState } from 'react'
import SettingsModal from '../components/SettingsModal'
import { useScreens } from '../hooks/useScreens'
import { useContent } from '../hooks/useContent'

export default function Dashboard() {
  const nav = useNavigate()
  const { data: screens = [] } = useScreens()
  const { data: media = [] } = useContent()
  const [settingsFor, setSettingsFor] = useState<Screen | null>(null)

  const online = screens.filter((s) => s.status === 'online').length

  const stats = [
    { lbl: 'Total screens', val: String(screens.length), ch: '↑ 1 this week', chCls: 'up', ico: '📺', icoCls: 'g' },
    { lbl: 'Online now', val: String(online), ch: '↑ Healthy', chCls: 'up', ico: '✅', icoCls: 'gr' },
    { lbl: 'Content items', val: String(media.length), ch: '↑ 3 new', chCls: 'up', ico: '🖼️', icoCls: 'am' },
    { lbl: 'Plays today', val: '—', ch: 'Enable reporting', chCls: 'nl', ico: '📊', icoCls: 'bl' },
  ]

  return (
    <div className="page">
      <div className="stats-row">
        {stats.map((s) => (
          <div className="sc" key={s.lbl}>
            <div className="sc-lbl">{s.lbl}</div>
            <div className="sc-val">{s.val}</div>
            <div className={`sc-ch ${s.chCls}`}>{s.ch}</div>
            <div className={`sc-ico ${s.icoCls}`}>{s.ico}</div>
          </div>
        ))}
      </div>

      <div className="sh">
        <span className="sh-t">Screens</span>
        <button className="btn btn-g btn-sm" onClick={() => nav('/screens')}>View all</button>
      </div>
      <div className="sg" style={{ marginBottom: 20 }}>
        {screens.map((s) => (
          <ScreenCard key={s.id} s={s} onSettings={setSettingsFor} />
        ))}
      </div>

      <div className="sh">
        <span className="sh-t">Recent content</span>
        <button className="btn btn-g btn-sm" onClick={() => nav('/content')}>View all</button>
      </div>
      <div className="mg">
        {media.slice(0, 4).map((m) => (
          <MediaCard key={m.id} m={m} />
        ))}
      </div>

      <SettingsModal open={settingsFor !== null} onClose={() => setSettingsFor(null)} screen={settingsFor ?? undefined} />
    </div>
  )
}
