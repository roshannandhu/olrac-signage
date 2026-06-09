const rows = [
  { time: 'Today 3:35 PM', pill: 'ps', action: 'Updated playlist', target: 'Lobby Display' },
  { time: 'Today 3:28 PM', pill: 'pg', action: 'Uploaded content', target: 'Demo HD video (beach)' },
  { time: 'Today 3:27 PM', pill: 'pa', action: 'Added screen', target: 'Lobby Display · Landscape · 0°' },
  { time: 'Today 3:20 PM', pill: 'ps', action: 'Logged in', target: 'Admin account' },
]

export default function Activity() {
  return (
    <div className="page">
      <div className="sh">
        <span className="sh-t">Activity log</span>
        <button className="btn btn-g btn-sm">↓ Export</button>
      </div>
      <div className="tw">
        <table className="gt">
          <thead>
            <tr>
              <th>Time</th>
              <th>User</th>
              <th>Action</th>
              <th>Target</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, color: 'var(--text3)' }}>{r.time}</td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <div className="av" style={{ width: 22, height: 22, fontSize: 10 }}>R</div>
                    Admin
                  </div>
                </td>
                <td><span className={`pill ${r.pill}`}>{r.action}</span></td>
                <td>{r.target}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
