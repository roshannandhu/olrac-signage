import { useState } from 'react'
import Modal, { ModalHeader } from './Modal'
import { useStore } from '../store'
import { exportReportCsv } from '../hooks/useReports'
import type { ReportRange } from '../api'

const options = [
  { key: 'summary', title: 'Summary', desc: 'Totals per content item' },
  { key: 'by-screen', title: 'Per-screen breakdown', desc: 'Totals per screen' },
  { key: 'hourly', title: 'Hourly detail', desc: 'Hour-by-hour per screen' },
]

export default function ExportModal({ open, onClose, range = {} }: { open: boolean; onClose: () => void; range?: ReportRange }) {
  const pushToast = useStore((s) => s.pushToast)
  const [selected, setSelected] = useState('summary')

  const handleExport = async () => {
    onClose()
    try {
      await exportReportCsv(selected as any, range)
      pushToast('Report exported!', 'success')
    } catch {
      pushToast('Failed to export report', 'error')
    }
  }

  return (
    <Modal open={open} onClose={onClose} small>
      <ModalHeader icon="📊" title="Export options" onClose={onClose} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 7, marginBottom: 16 }}>
        {options.map((o) => (
          <label
            key={o.key}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: 11,
              border: `1.5px solid ${selected === o.key ? 'var(--accent)' : 'var(--border2)'}`,
              borderRadius: 'var(--r-sm)',
              cursor: 'pointer',
              background: selected === o.key ? 'var(--sl-bg)' : 'transparent',
            }}
          >
            <input
              type="radio"
              name="exp"
              checked={selected === o.key}
              onChange={() => setSelected(o.key)}
              style={{ accentColor: 'var(--accent)' }}
            />
            <div>
              <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--text)' }}>{o.title}</div>
              <div style={{ fontSize: 11, color: 'var(--text3)' }}>{o.desc}</div>
            </div>
          </label>
        ))}
      </div>
      <div className="mf">
        <button className="btn btn-g" onClick={onClose}>Cancel</button>
        <button className="btn btn-p" onClick={handleExport}>
          ↓ Export
        </button>
      </div>
    </Modal>
  )
}
