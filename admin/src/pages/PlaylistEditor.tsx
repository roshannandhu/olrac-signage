import { useMemo, useRef, useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStore } from '../store'
import type { Media } from '../types'
import SettingsModal from '../components/SettingsModal'
import UploadModal from '../components/UploadModal'

import { useScreens } from '../hooks/useScreens'
import { useContent } from '../hooks/useContent'
import { usePlaylist, useSavePlaylist } from '../hooks/usePlaylist'
import { contentToMedia } from '../api'

interface PlaylistItemUI extends Media {
  uniqueId: string
  content_id: string
  duration_override?: number | null
}

export default function PlaylistEditor() {
  const { selectedScreen, pushToast } = useStore()
  const nav = useNavigate()

  const { data: screens = [] } = useScreens()
  const { data: media = [] } = useContent()

  const screen = useMemo(
    () => screens.find((s) => s.name === selectedScreen) ?? screens[0],
    [screens, selectedScreen]
  )

  const { data: serverPlaylist } = usePlaylist(screen?.id)
  const { mutate: savePlaylist } = useSavePlaylist()

  const [playlist, setPlaylist] = useState<PlaylistItemUI[]>([])
  const [dirty, setDirty] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const dragIndex = useRef<number | null>(null)
  const [dragging, setDragging] = useState<number | null>(null)

  // Seed once + don't overwrite if dirty
  useEffect(() => {
    if (serverPlaylist && !dirty) {
      setPlaylist(
        serverPlaylist.map((dto) => ({
          ...contentToMedia(dto.content as any),
          uniqueId: dto.id,
          content_id: dto.content.id,
          duration_override: dto.duration_override,
        }))
      )
    }
  }, [serverPlaylist, dirty])

  const add = (m: Media) => {
    setPlaylist((p) => [
      ...p,
      { ...m, uniqueId: `${m.id}-${Date.now()}`, content_id: m.id, duration_override: null },
    ])
    setDirty(true)
    const short = m.name.split(' ').slice(0, 3).join(' ')
    pushToast(`Added ${m.ico} ${short}…`, 'success')
  }

  const remove = (i: number) => {
    setPlaylist((p) => p.filter((_, idx) => idx !== i))
    setDirty(true)
  }

  const save = () => {
    if (!screen?.id) return
    const items = playlist.map((item, idx) => ({
      content_id: item.content_id,
      position: idx,
      duration_override: item.duration_override ?? null,
    }))
    savePlaylist({ screenId: screen.id, items })
    setDirty(false)
  }

  const onDrop = (target: number) => {
    const from = dragIndex.current
    setDragging(null)
    dragIndex.current = null
    if (from === null || from === target) return
    setPlaylist((p) => {
      const next = [...p]
      const [moved] = next.splice(from, 1)
      next.splice(target, 0, moved)
      return next
    })
    setDirty(true)
  }

  const offline = screen?.status === 'offline'

  return (
    <div className="page">
      <div className="sh" style={{ marginBottom: 12 }}>
        <button className="btn btn-g btn-sm" onClick={() => nav('/screens')}>
          ← Back
        </button>
        <div style={{ flex: 1, marginLeft: 8 }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text)' }}>
            {screen?.name ?? 'Screen'}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text3)' }}>
            {screen?.orientLabel} · {screen?.deg}° {screen?.description ? `· ${screen.description}` : ''}
          </div>
        </div>
        <span className={`pill ${offline ? 'pr' : 'pg'}`}>● {offline ? 'Offline' : 'Online'}</span>
        <button className="btn btn-g btn-sm" onClick={() => setShowSettings(true)}>
          ⚙ Settings
        </button>
        <button className="btn btn-g btn-sm">⏰ Hours</button>
      </div>

      <div className="pl-layout">
        {/* Playlist panel */}
        <div className="pl-panel">
          <div className="ph">
            <span className="ph-t">Playlist</span>
            <button
              className="btn btn-p btn-sm"
              style={{ opacity: dirty ? 1 : 0.35, pointerEvents: dirty ? 'all' : 'none' }}
              onClick={save}
            >
              Save Changes
            </button>
          </div>
          <div className="pb">
            {playlist.length === 0 ? (
              <div className="pl-empty">
                <div className="pl-ei">⬇</div>
                <div style={{ fontSize: 12 }}>Click + on items from the right to build your playlist</div>
              </div>
            ) : (
              <div>
                {playlist.map((m, i) => (
                  <div
                    key={m.uniqueId}
                    className={`pl-item${dragging === i ? ' dragging' : ''}`}
                    draggable
                    onDragStart={(e) => {
                      dragIndex.current = i
                      setDragging(i)
                      // Firefox only starts a drag if dataTransfer is set.
                      e.dataTransfer.effectAllowed = 'move'
                      e.dataTransfer.setData('text/plain', String(i))
                    }}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={() => onDrop(i)}
                    onDragEnd={() => setDragging(null)}
                  >
                    <span className="dh">⠿</span>
                    <div className="pit" style={{ background: m.bg }}>
                      {m.ico}
                    </div>
                    <div className="pii">
                      <div className="pin">{m.name}</div>
                      <div className="pim">
                        {m.type} · {m.orient}
                      </div>
                    </div>
                    {m.dur ? <span className="pid">{m.dur}</span> : null}
                    <span className="prm" onClick={() => remove(i)}>
                      ✕
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Library panel */}
        <div className="lib-panel">
          <div className="ph">
            <span className="ph-t">Content library</span>
            <button
              className="btn btn-g btn-sm"
              style={{ padding: '3px 7px' }}
              onClick={() => setShowUpload(true)}
            >
              ↑
            </button>
            <button className="btn btn-g btn-sm" style={{ padding: '3px 7px' }}>
              ↕
            </button>
            <button className="btn btn-g btn-sm" style={{ padding: '3px 7px' }}>
              ⚡
            </button>
          </div>
          <div className="pb">
            {media.map((m) => (
              <div className="li" key={m.id} onClick={() => add(m)}>
                <div className="lt" style={{ background: m.bg }}>
                  {m.ico}
                </div>
                <div className="lii">
                  <div className="ln">{m.name}</div>
                  <div className="lm">
                    {m.type} · {m.orient}
                    {m.dur ? ` · ${m.dur}` : ''}
                  </div>
                </div>
                <div className="ladd">+</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <SettingsModal open={showSettings} onClose={() => setShowSettings(false)} screen={screen} />
      <UploadModal open={showUpload} onClose={() => setShowUpload(false)} />
    </div>
  )
}
