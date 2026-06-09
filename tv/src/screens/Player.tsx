import { useCallback, useEffect, useRef, useState } from 'react'
import { SLIDES, SLIDE_DURATION, SCREEN_NAME, SCREEN_ORIENTATION_DEG } from '../data'
import { fetchMe } from '../api'
import { startHeartbeat } from '../services/heartbeat'
import { PlaybackLogger } from '../services/playbackLogger'

// Use real API later
const USE_PROD_API = true

// Container rotation for the four mounting orientations (D0/D90/D180/D270).
function rotStyle(deg: number): React.CSSProperties {
  if (deg === 90 || deg === 270) {
    return {
      width: '100vh',
      height: '100vw',
      left: '50%',
      top: '50%',
      transform: `translate(-50%, -50%) rotate(${deg}deg)`,
    }
  }
  return { width: '100%', height: '100%', transform: `rotate(${deg}deg)` }
}

export default function Player({ onExit }: { onExit: () => void }) {
  // In demo mode, we use SLIDES. In prod, we'd use fetched playlist.
  const [playlist, setPlaylist] = useState<any[]>(SLIDES)
  const [cur, setCur] = useState(0)
  const [paused, setPaused] = useState(false)
  const [hudVis, setHudVis] = useState(false)
  const [clock, setClock] = useState('--:--')
  
  // Production Offline/Cache state
  const [isOffline, setIsOffline] = useState(false)
  const [cachedBlobs, setCachedBlobs] = useState<Record<string, string>>({})
  const [orientationDeg, setOrientationDeg] = useState<number>(SCREEN_ORIENTATION_DEG)

  const progRef = useRef<HTMLDivElement>(null)
  const elapsedRef = useRef(0)
  const hudTimer = useRef<number | null>(null)
  const touchX = useRef<number | null>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const loggerRef = useRef<PlaybackLogger | null>(null)

  const N = playlist.length || 1

  // ── PRODUCTION HOOKS (TODO-ready) ────────────────────────────────────
  useEffect(() => {
    if (!USE_PROD_API) return
    const token = localStorage.getItem('screen_token')
    if (!token) return

    loggerRef.current = new PlaybackLogger(token)

    let cleanupHeartbeat: () => void
    let pollInterval: number

    const init = async () => {
      try {
        const data = await fetchMe(token)
        setIsOffline(false)
        const normalize = (items: any[]) => items.map(item => {
          if (item.content) {
            return {
              type: item.content.type,
              url: item.content.public_url,
              duration: (item.duration_override || item.content.duration_seconds || 10) * 1000,
              original: item
            }
          }
          return item
        })
        const newPlaylist = data.playlist.length ? normalize(data.playlist) : SLIDES
        setPlaylist(newPlaylist)
        localStorage.setItem('cached_playlist', JSON.stringify(newPlaylist))
        
        const degFromEnum = (o: string) => o === 'D90' ? 90 : o === 'D180' ? 180 : o === 'D270' ? 270 : 0;
        setOrientationDeg(degFromEnum(data.screen.orientation))
        
        cleanupHeartbeat = startHeartbeat(data.screen.id, token)

        pollInterval = window.setInterval(async () => {
          try {
            const fresh = await fetchMe(token)
            setIsOffline(false)
            setPlaylist(prev => {
              if (JSON.stringify(fresh.playlist) !== JSON.stringify(prev)) {
                const newPlaylist = fresh.playlist.length ? normalize(fresh.playlist) : SLIDES
                localStorage.setItem('cached_playlist', JSON.stringify(newPlaylist))
                return newPlaylist
              }
              return prev
            })
            setOrientationDeg(degFromEnum(fresh.screen.orientation))
          } catch (e) {
            setIsOffline(true)
          }
        }, 30000)
      } catch (e) {
        setIsOffline(true)
        const cached = localStorage.getItem('cached_playlist')
        if (cached) setPlaylist(JSON.parse(cached))
      }
    }

    init()

    return () => {
      if (cleanupHeartbeat) cleanupHeartbeat()
      if (pollInterval) window.clearInterval(pollInterval)
      if (loggerRef.current) loggerRef.current.destroy()
    }
  }, [])

  useEffect(() => {
    if (!USE_PROD_API) return
    
    const cacheMedia = async () => {
      try {
        const cache = await caches.open('tv-media-cache');
        const newBlobs: Record<string, string> = { ...cachedBlobs };
        let changed = false;

        for (const item of playlist) {
          const url = item.url || item.content?.public_url;
          const id = item?.original?.content?.id || item?.content?.id || url;
          if (!url || !id) continue;
          if (newBlobs[id]) continue;

          const cachedRes = await cache.match(url);
          if (cachedRes) {
            const blob = await cachedRes.blob();
            newBlobs[id] = URL.createObjectURL(blob);
            changed = true;
          } else {
            try {
              const res = await fetch(url);
              if (res.ok) {
                await cache.put(url, res.clone());
                const blob = await res.blob();
                newBlobs[id] = URL.createObjectURL(blob);
                changed = true;
              }
            } catch (e) {
              console.warn("Failed to download", url);
            }
          }
        }
        if (changed) setCachedBlobs(newBlobs);
      } catch (e) {
        console.warn("Cache API not supported or failed", e);
      }
    };
    cacheMedia();
  }, [playlist])

  // ── HUD show/auto-hide ───────────────────────────────────────────────
  const showHud = useCallback(() => {
    setHudVis(true)
    if (hudTimer.current) window.clearTimeout(hudTimer.current)
    hudTimer.current = window.setTimeout(() => setHudVis(false), 4000)
  }, [])
  const toggleHud = useCallback(() => {
    if (hudVis) {
      setHudVis(false)
      if (hudTimer.current) window.clearTimeout(hudTimer.current)
    } else {
      showHud()
    }
  }, [hudVis, showHud])

  // ── clock + initial HUD ──────────────────────────────────────────────
  useEffect(() => {
    const tick = () => {
      const n = new Date()
      setClock(`${String(n.getHours()).padStart(2, '0')}:${String(n.getMinutes()).padStart(2, '0')}`)
    }
    tick()
    const id = window.setInterval(tick, 1000)
    showHud()
    return () => window.clearInterval(id)
  }, [showHud])

  // ── playback logging ─────────────────────────────────────────────────
  const logPlayback = useCallback((item: any, durationMs: number) => {
    if (!USE_PROD_API || !loggerRef.current) return
    const contentId = item?.original?.content?.id || item?.content?.id
    if (!contentId) return
    loggerRef.current.log({
      content_id: contentId,
      played_at: new Date(Date.now() - durationMs).toISOString(),
      duration_played: Math.floor(durationMs / 1000)
    })
  }, [])

  // ── navigation ───────────────────────────────────────────────────────
  const goTo = useCallback((n: number) => {
    if (elapsedRef.current > 1000) {
      logPlayback(playlist[cur], elapsedRef.current)
    }
    elapsedRef.current = 0
    if (progRef.current) progRef.current.style.width = '0%'
    setCur(((n % N) + N) % N)
    if (videoRef.current) {
      videoRef.current.currentTime = 0
      if (!paused) videoRef.current.play().catch(() => {})
    }
  }, [N, paused, playlist, cur, logPlayback])
  const next = useCallback(() => goTo(cur + 1), [cur, goTo])
  const prev = useCallback(() => goTo(cur - 1), [cur, goTo])

  // ── progress + auto-advance (rAF, respects pause) ────────────────────
  useEffect(() => {
    if (paused) {
      if (videoRef.current) videoRef.current.pause()
      return
    } else {
      if (videoRef.current) {
        if (elapsedRef.current === 0) {
          videoRef.current.currentTime = 0
        }
        videoRef.current.play().catch(() => {})
      }
    }

    const currentItem = playlist[cur]
    const duration = currentItem?.duration ?? SLIDE_DURATION
    const isVideo = currentItem?.type === 'video'

    let raf = 0
    let start = performance.now() - elapsedRef.current
    const loop = (now: number) => {
      const e = now - start
      elapsedRef.current = e
      
      const pct = Math.min((e / duration) * 100, 100)
      if (progRef.current && !isVideo) progRef.current.style.width = `${pct}%`

      if (!isVideo && e >= duration) {
        logPlayback(currentItem, duration)
        elapsedRef.current = 0
        if (N === 1) {
          start = now
        } else {
          setCur((c) => (c + 1) % N)
          return
        }
      }
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(raf)
  }, [cur, paused, playlist, N, logPlayback])

  // ── keyboard shortcuts ───────────────────────────────────────────────
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') next()
      else if (e.key === 'ArrowLeft') prev()
      else if (e.key === ' ') {
        e.preventDefault()
        setPaused((p) => !p)
      } else if (e.key === 'i' || e.key === 'I') toggleHud()
      else if (e.key === 'Escape') onExit()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [next, prev, toggleHud, onExit])

  return (
    <div
      className="scr scr-player"
      onTouchStart={(e) => (touchX.current = e.touches[0].clientX)}
      onTouchEnd={(e) => {
        if (touchX.current === null) return
        const dx = e.changedTouches[0].clientX - touchX.current
        if (Math.abs(dx) > 55) (dx < 0 ? next() : prev())
        touchX.current = null
      }}
    >
      {/* rotating stage */}
      <div className="rot" style={rotStyle(orientationDeg)}>
        {playlist.map((s, i) => {
          const isActive = i === cur
          const isVideo = s?.type === 'video'
          const isImage = s?.type === 'image'
          const blobId = s?.original?.content?.id || s?.content?.id || s?.url;
          const blobUrl = cachedBlobs[blobId] || s?.url || s?.content?.public_url
          
          return (
            <div key={i} className={`slide ${s.cls || 's0'}${isActive ? ' active' : ''}`}>
              {/* Production Media */}
              {isVideo && (
                <video 
                  ref={isActive ? videoRef : undefined}
                  src={blobUrl} 
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  onEnded={() => {
                    if (isActive) {
                      logPlayback(s, videoRef.current?.duration ? videoRef.current.duration * 1000 : 0)
                      elapsedRef.current = 0
                      if (N === 1) {
                        if (videoRef.current) {
                          videoRef.current.currentTime = 0
                          videoRef.current.play().catch(() => {})
                        }
                      } else {
                        setCur((c) => (c + 1) % N)
                      }
                    }
                  }}
                  onTimeUpdate={(e) => {
                    if (!isActive) return
                    const v = e.currentTarget
                    if (progRef.current && v.duration) {
                      progRef.current.style.width = `${(v.currentTime / v.duration) * 100}%`
                    }
                  }}
                  muted
                  playsInline
                />
              )}
              {isImage && (
                <img src={blobUrl} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              )}
              
              {/* Demo mode fallback UI */}
              {!isVideo && !isImage && s.emoji && (
                <>
                  <div className="slide-emoji">{s.emoji}</div>
                  <div className="slide-caption">
                    <div className="cap-title">{s.title}</div>
                    <div className="cap-sub">{s.sub}</div>
                  </div>
                </>
              )}
            </div>
          )
        })}
      </div>

      {/* HUD */}
      <div className={`hud${hudVis ? ' vis' : ''}`}>
        <div className="hud-left">
          <div className="hud-ico">📺</div>
          <span className="hud-nm">Olrac Signage · {SCREEN_NAME}</span>
        </div>
        <div className="hud-right">
          <div className="hud-clock">{clock}</div>
          <div className="hud-status" style={isOffline ? { color: 'var(--red)', borderColor: 'rgba(239,68,68,0.25)', background: 'rgba(239,68,68,0.15)' } : {}}>
            <div className="hud-dot" style={isOffline ? { background: 'var(--red)' } : {}} />
            {isOffline ? 'Offline (Cached)' : 'Online'}
          </div>
        </div>
      </div>

      <div className="prog-bar">
        <div className="prog-fill" ref={progRef} />
      </div>

      <div className="dots">
        {playlist.map((_, i) => (
          <div key={i} className={`dot${i === cur ? ' active' : ''}`} />
        ))}
      </div>

      <div className="remote">
        <div className="rl">Remote</div>
        <div className="rb" onClick={prev}>◀</div>
        <div className="rrow">
          <div className="rb" onClick={toggleHud}>ℹ</div>
          <div className="rb" onClick={() => setPaused((p) => !p)}>{paused ? '▶' : '⏸'}</div>
        </div>
        <div className="rb" onClick={next}>▶</div>
        <button className="exit-b" onClick={onExit}>✕ Exit</button>
      </div>
    </div>
  )
}
