import { useState, useMemo } from 'react'
import ExportModal from '../components/ExportModal'
import { useReports } from '../hooks/useReports'
import { formatDuration } from '../api'

export default function Reports() {
  const [showExport, setShowExport] = useState(false)
  const [rangeStr, setRangeStr] = useState('Last 7 days')

  const range = useMemo(() => {
    if (rangeStr === 'Last 30 days') {
      const d = new Date()
      d.setDate(d.getDate() - 30)
      return { from: d.toISOString() }
    }
    if (rangeStr === 'This month') {
      const d = new Date()
      d.setDate(1)
      d.setHours(0, 0, 0, 0)
      return { from: d.toISOString() }
    }
    return {}
  }, [rangeStr])

  const { data: rows = [], refetch } = useReports('summary', range)

  return (
    <div className="page">
      <div className="sh">
        <span className="sh-t">Playback report</span>
        <span className="pill ps" style={{ marginLeft: 'auto' }}>1 screen reporting</span>
        <button className="btn btn-g btn-sm">Enable Reporting</button>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 16, flexWrap: 'wrap' }}>
        <select
          value={rangeStr}
          onChange={(e) => setRangeStr(e.target.value)}
          style={{
            padding: '6px 12px',
            border: '1.5px solid var(--border2)',
            borderRadius: 8,
            fontFamily: "'Outfit',sans-serif",
            fontSize: 12.5,
            color: 'var(--text)',
            background: '#fff',
            outline: 'none',
            cursor: 'pointer',
          }}
        >
          <option>Last 7 days</option>
          <option>Last 30 days</option>
          <option>This month</option>
        </select>
        <button className="btn btn-g btn-sm" onClick={() => refetch()}>↺ Refresh</button>
        <button className="btn btn-g btn-sm" onClick={() => setShowExport(true)}>↓ Export</button>
        <button className="btn btn-g btn-sm">⚡ Filters</button>
      </div>

      <div className="tw">
        <table className="gt">
          <thead>
            <tr>
              <th>Item</th>
              <th>Type</th>
              <th>Screens</th>
              <th>Play count</th>
              <th>Total duration</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text3)', padding: 38, fontSize: 12.5 }}>
                  Screens report playback data periodically. Data will appear once your screens have sent their first reports.
                </td>
              </tr>
            ) : (
              (rows as any[]).map((r, i) => (
                <tr key={r.content_id || i}>
                  <td>{r.name}</td>
                  <td style={{ textTransform: 'capitalize' }}>{r.type}</td>
                  <td>{r.screen_count}</td>
                  <td>{r.play_count}</td>
                  <td>{formatDuration(r.total_duration) || '0:00'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <ExportModal open={showExport} onClose={() => setShowExport(false)} range={range} />
    </div>
  )
}
