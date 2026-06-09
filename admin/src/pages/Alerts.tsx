import { useState } from 'react'

interface Alert {
  id: string
  kind: 'red' | 'amber'
  ico: string
  title: string
  sub: string
  border: string
  bg: string
}

const initial: Alert[] = [
  {
    id: 'a1',
    kind: 'red',
    ico: '🔴',
    title: 'Cafeteria Board went offline',
    sub: '3 hours ago · Last seen 12:28 PM',
    border: '#FECACA',
    bg: 'var(--red-bg)',
  },
  {
    id: 'a2',
    kind: 'amber',
    ico: '⚠️',
    title: 'Content "Demo video (beach)" expiring soon',
    sub: 'Expires in 2 days · Used on 1 screen',
    border: '#FDE68A',
    bg: 'var(--amber-bg)',
  },
]

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>(initial)

  return (
    <div className="page">
      <div className="sh">
        <span className="sh-t">Alerts</span>
        <button className="btn btn-p btn-sm">+ New Alert</button>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
        {alerts.map((a) => (
          <div
            key={a.id}
            style={{
              background: '#fff',
              border: `1px solid ${a.border}`,
              borderRadius: 'var(--r)',
              padding: '13px 16px',
              display: 'flex',
              alignItems: 'center',
              gap: 11,
            }}
          >
            <div style={{ width: 36, height: 36, borderRadius: 8, background: a.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 17, flexShrink: 0 }}>
              {a.ico}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{a.title}</div>
              <div style={{ fontSize: 11, color: 'var(--text3)' }}>{a.sub}</div>
            </div>
            <button className="btn btn-g btn-sm" onClick={() => setAlerts((list) => list.filter((x) => x.id !== a.id))}>
              Dismiss
            </button>
          </div>
        ))}
        {alerts.length === 0 && (
          <div className="empt">
            <div className="ei">🔔</div>
            <div className="et">No active alerts</div>
            <div className="ed">You're all caught up. Screen and content alerts will appear here.</div>
          </div>
        )}
      </div>
    </div>
  )
}
