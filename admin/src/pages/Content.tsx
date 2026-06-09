import { useState } from 'react'
import { useStore } from '../store'
import { useContent } from '../hooks'
import type { ContentFilters } from '../api'
import type { Media } from '../types'
import MediaCard from '../components/MediaCard'
import SortMenu from '../components/SortMenu'
import UploadModal from '../components/UploadModal'

const SORT_MAP: Record<string, ContentFilters['sort']> = {
  'Date added (newest)': 'newest',
  'Date added (oldest)': 'oldest',
  'Alphabetical A–Z': 'az',
  'Alphabetical Z–A': 'za',
}

function sortMock(items: Media[], option: string): Media[] {
  const arr = [...items]
  if (option === 'Alphabetical A–Z') arr.sort((a, b) => a.name.localeCompare(b.name))
  else if (option === 'Alphabetical Z–A') arr.sort((a, b) => b.name.localeCompare(a.name))
  return arr
}

export default function Content() {
  const mockMedia = useStore((s) => s.media)
  const [showFilters, setShowFilters] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const [sortOption, setSortOption] = useState('Date added (newest)')
  const [filters, setFilters] = useState({ video: true, image: true, landscape: true, portrait: true })

  const toggle = (k: keyof typeof filters) => setFilters((f) => ({ ...f, [k]: !f[k] }))

  const apiFilters: ContentFilters = {
    type:
      filters.video && !filters.image ? 'video'
      : !filters.video && filters.image ? 'image'
      : undefined,
    orientation:
      filters.landscape && !filters.portrait ? 'landscape'
      : !filters.landscape && filters.portrait ? 'portrait'
      : undefined,
    sort: SORT_MAP[sortOption] ?? 'newest',
  }

  const { data: apiData, isLoading } = useContent(apiFilters)

  // Use live API data when the backend is up; fall back to client-filtered mock otherwise.
  const visible: Media[] = apiData ?? sortMock(
    mockMedia.filter((m) => {
      if (m.type === 'Video' && !filters.video) return false
      if (m.type === 'Image' && !filters.image) return false
      if (m.orient === 'landscape' && !filters.landscape) return false
      if (m.orient === 'portrait' && !filters.portrait) return false
      return true
    }),
    sortOption,
  )

  return (
    <div className="page">
      <div className="sh">
        <span className="sh-t">Content library</span>
        <div className="tb">
          <SortMenu onChange={setSortOption} />
          <button className="btn btn-g btn-sm" onClick={() => setShowFilters((v) => !v)}>⚡ Filters</button>
          <button className="btn btn-p btn-sm" onClick={() => setShowUpload(true)}>+ Upload Files</button>
        </div>
      </div>

      <div className={`fp${showFilters ? ' open' : ''}`}>
        <div className="fr">
          <div>
            <div className="fl2">Media type</div>
            <div className="tg">
              <button className={`tb2${filters.video ? ' active' : ''}`} onClick={() => toggle('video')}>Videos</button>
              <button className={`tb2${filters.image ? ' active' : ''}`} onClick={() => toggle('image')}>Images</button>
            </div>
          </div>
          <div style={{ marginLeft: 18 }}>
            <div className="fl2">Orientation</div>
            <div className="tg">
              <button className={`tb2${filters.landscape ? ' active' : ''}`} onClick={() => toggle('landscape')}>Landscape</button>
              <button className={`tb2${filters.portrait ? ' active' : ''}`} onClick={() => toggle('portrait')}>Portrait</button>
            </div>
          </div>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 6, alignItems: 'flex-end' }}>
            <button
              className="btn btn-g btn-sm"
              onClick={() => setFilters({ video: true, image: true, landscape: true, portrait: true })}
            >
              Reset
            </button>
            <button className="btn btn-p btn-sm" onClick={() => setShowFilters(false)}>Apply</button>
          </div>
        </div>
      </div>

      {isLoading && !apiData ? (
        <div className="mg">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="mc" style={{ pointerEvents: 'none', animationDelay: `${i * 0.04}s` }}>
              <div className="mth" style={{ background: 'var(--sl-bg)' }} />
              <div className="mi">
                <div style={{ height: 13, width: '75%', background: 'var(--border)', borderRadius: 4, marginBottom: 6 }} />
                <div style={{ height: 11, width: '50%', background: 'var(--border)', borderRadius: 4 }} />
              </div>
            </div>
          ))}
        </div>
      ) : visible.length === 0 ? (
        <div className="empt">
          <div className="ei">🖼️</div>
          <div className="et">No content yet</div>
          <div className="ed">Upload images or videos to get started. Supported formats: MP4, MOV, JPG, PNG.</div>
          <button className="btn btn-p" onClick={() => setShowUpload(true)}>+ Upload Files</button>
        </div>
      ) : (
        <div className="mg">
          {visible.map((m) => (
            <MediaCard key={m.id} m={m} />
          ))}
        </div>
      )}

      <UploadModal open={showUpload} onClose={() => setShowUpload(false)} />
    </div>
  )
}
