import { useState } from 'react'
import SortMenu from '../components/SortMenu'
import WebsiteModal from '../components/WebsiteModal'
import { useWebsites } from '../hooks/useWebsites'

export default function Websites() {
  const { data: websites = [] } = useWebsites()
  const [showModal, setShowModal] = useState(false)

  return (
    <div className="page">
      <div className="sh">
        <span className="sh-t">Websites</span>
        <div className="tb">
          <SortMenu options={['Date added (newest)', 'Date added (oldest)', 'Alphabetical A–Z', 'Alphabetical Z–A']} />
          <button className="btn btn-p btn-sm" onClick={() => setShowModal(true)}>+ Add Website</button>
        </div>
      </div>
      <div className="mg">
        {websites.map((w) => (
          <div className="mc" key={w.id}>
            <div className="mth">
              <div className="mtp" style={{ background: '#F0F9FF' }}>🌐</div>
              <div className="mtype">🌐</div>
            </div>
            <div className="mi">
              <div className="mn">{w.name}</div>
              <div className="mm">Website · {w.addedAt}</div>
            </div>
            <div className="mmenu">⋮</div>
          </div>
        ))}
      </div>

      <WebsiteModal open={showModal} onClose={() => setShowModal(false)} />
    </div>
  )
}
