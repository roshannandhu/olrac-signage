import { useState } from 'react'
import { useStore } from '../store'
import { useGroups, useCreateGroup, useDeleteGroup } from '../hooks/useGroups'
import { useScreens } from '../hooks/useScreens'

export default function Groups() {
  const { pushToast } = useStore()
  const { data: groups = [] } = useGroups()
  const { data: screens = [] } = useScreens()
  const { mutate: createGroup } = useCreateGroup()
  const { mutate: deleteGroup } = useDeleteGroup()

  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [checked, setChecked] = useState<string[]>([])

  const toggle = (id: string) => setChecked((c) => (c.includes(id) ? c.filter((x) => x !== id) : [...c, id]))

  const create = () => {
    if (!name.trim()) {
      pushToast('Please enter a group name', 'error')
      return
    }
    createGroup({ name: name.trim(), screen_ids: checked })
    setName('')
    setChecked([])
    setOpen(false)
  }

  const del = (id: string, groupName: string) => {
    if (window.confirm(`Are you sure you want to remove the group "${groupName}"?`)) {
      deleteGroup(id)
    }
  }

  return (
    <div className="page">
      <div className="sh">
        <span className="sh-t">Screen groups</span>
        <button className="btn btn-p btn-sm" onClick={() => setOpen(true)}>+ Add Screen Group</button>
      </div>

      {open && (
        <div className="new-grp">
          <div style={{ fontSize: 13.5, fontWeight: 700, color: 'var(--text)', marginBottom: 12 }}>New screen group</div>
          <div className="fg">
            <label className="fl">Group name *</label>
            <input className="fi2" type="text" placeholder="e.g. Lobby Screens" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
          </div>
          <div className="fg">
            <label className="fl">Assign screens</label>
            <div className="scl">
              {screens.map((s) => (
                <label key={s.id}>
                  <input
                    type="checkbox"
                    checked={checked.includes(s.id)}
                    onChange={() => toggle(s.id)}
                    style={{ accentColor: 'var(--accent)', width: 14, height: 14 }}
                  />
                  <div>
                    <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--text)' }}>{s.name}</div>
                    <div style={{ fontSize: 10.5, color: 'var(--text3)' }}>
                      {s.status === 'online' ? 'Online' : 'Offline'} · {s.orientLabel} · {s.deg}°
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 7, marginTop: 6 }}>
            <button className="btn btn-g btn-sm" onClick={() => setOpen(false)}>Cancel</button>
            <button className="btn btn-p btn-sm" onClick={create}>Create Group</button>
          </div>
        </div>
      )}

      {groups.length > 0 ? (
        <div className="grp-grid">
          {groups.map((g) => (
            <div className="gc" key={g.id}>
              <div className="gch">
                <div className="gico">📺</div>
                <div>
                  <div className="gnm">{g.name}</div>
                  <div className="gsub">{g.screens.length} screen{g.screens.length !== 1 ? 's' : ''}</div>
                </div>
              </div>
              <div className="gs">
                {g.screens.length > 0 ? (
                  g.screens.map((s) => <span className="st" key={s}>{s}</span>)
                ) : (
                  <span className="st" style={{ color: 'var(--text3)' }}>No screens assigned</span>
                )}
              </div>
              <div className="gac">
                <button className="btn btn-g btn-sm">Edit Playlist</button>
                <button className="btn btn-d btn-sm" onClick={() => del(g.id, g.name)}>Remove</button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        !open && (
          <div className="empt">
            <div className="ei">🖥️</div>
            <div className="et">No screen groups yet</div>
            <div className="ed">
              Group multiple screens that share the same playlist. Create a group, assign screens, manage one playlist for all of them.
            </div>
            <button className="btn btn-p" onClick={() => setOpen(true)}>+ Add Screen Group</button>
          </div>
        )
      )}
    </div>
  )
}
