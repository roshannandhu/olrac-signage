import type { Media } from '../types'

export default function MediaCard({ m }: { m: Media }) {
  return (
    <div className="mc">
      <div className="mth">
        <div className="mtp" style={{ background: m.bg }}>{m.ico}</div>
        {m.dur ? <div className="mbadge">{m.dur}</div> : null}
        <div className="mtype">{m.type === 'Video' ? '▶' : '📷'}</div>
      </div>
      <div className="mi">
        <div className="mn" title={m.name}>{m.name}</div>
        <div className="mm">{m.type} · {m.orient} · 2h ago</div>
      </div>
      <div className="mmenu">⋮</div>
    </div>
  )
}
