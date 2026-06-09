import { useEffect, useState } from 'react'
import Modal, { ModalHeader } from './Modal'
import { useStore } from '../store'
import { useUpdateScreen, useDeleteScreen } from '../hooks'
import type { OrientationEnum } from '../api'
import type { Screen } from '../types'

// When Supabase is not yet configured we skip the real API and save locally (demo mode)
const SUPABASE_CONFIGURED =
  !!import.meta.env.VITE_SUPABASE_URL &&
  !(import.meta.env.VITE_SUPABASE_URL as string).includes('YOUR-PROJECT')

const ORIENT_OPTIONS = [
  'Landscape (+ 0°)',
  'Portrait (+ 90°)',
  'Upside Down (+ 180°)',
  'Reverse Portrait (+ 270°)',
]

const degToOption = (deg: number) =>
  deg === 90 ? ORIENT_OPTIONS[1]
  : deg === 180 ? ORIENT_OPTIONS[2]
  : deg === 270 ? ORIENT_OPTIONS[3]
  : ORIENT_OPTIONS[0]

const optionToEnum = (option: string): OrientationEnum =>
  option.includes('90') ? 'D90'
  : option.includes('180') ? 'D180'
  : option.includes('270') ? 'D270'
  : 'D0'

export default function SettingsModal({
  open,
  onClose,
  screen,
}: {
  open: boolean
  onClose: () => void
  screen?: Screen
}) {
  const pushToast = useStore((s) => s.pushToast)
  const updateScreen = useUpdateScreen()

  // Controlled fields. The modal stays mounted (CSS-hidden), so we must reset
  // these whenever it opens for a (possibly different) screen — otherwise the
  // fields would keep stale values from the previously edited screen.
  const [orientation, setOrientation] = useState(ORIENT_OPTIONS[0])
  const [name, setName]               = useState('')
  const [description, setDescription] = useState('')
  const [tags, setTags]               = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)

  useEffect(() => {
    if (!open) return
    setOrientation(degToOption(screen?.deg ?? 0))
    setName(screen?.name ?? '')
    setDescription(screen?.description ?? '')
    setTags('')
    setConfirmDelete(false)
  }, [open, screen])

  const deleteScreen = useDeleteScreen()

  const save = () => {
    if (!screen) return
    if (!SUPABASE_CONFIGURED) {
      onClose()
      pushToast('Settings saved', 'success')
      return
    }
    updateScreen.mutate(
      {
        id: screen.id,
        body: { name, description, orientation: optionToEnum(orientation), tags: tags || undefined },
      },
      { onSuccess: onClose },
    )
  }

  const handleDelete = () => {
    if (!screen) return
    if (confirmDelete) {
      deleteScreen.mutate(screen.id, { onSuccess: onClose })
    } else {
      setConfirmDelete(true)
    }
  }

  return (
    <Modal open={open} onClose={onClose}>
      <ModalHeader icon="⚙️" title="Screen settings" onClose={onClose} />
      <div className="fg">
        <label className="fl">Screen orientation</label>
        <select
          className="fi2 fsel"
          value={orientation}
          onChange={(e) => setOrientation(e.target.value)}
        >
          {ORIENT_OPTIONS.map((o) => (
            <option key={o}>{o}</option>
          ))}
        </select>
      </div>
      <div className="fg">
        <label className="fl">Name *</label>
        <input
          className="fi2"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </div>
      <div className="fg">
        <label className="fl">Description</label>
        <input
          className="fi2"
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Add a description…"
        />
      </div>
      <div className="fg">
        <label className="fl">Tags</label>
        <input
          className="fi2"
          type="text"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          placeholder="Enter tags, comma-separated…"
        />
      </div>
      <div className="mf" style={{ justifyContent: 'space-between' }}>
        <div>
          <button
            className={`btn ${confirmDelete ? 'btn-r' : 'btn-g'}`}
            disabled={deleteScreen.isPending}
            onClick={handleDelete}
          >
            {deleteScreen.isPending ? 'Deleting…' : confirmDelete ? 'Are you sure? Delete Screen' : 'Delete Screen'}
          </button>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-g" onClick={onClose}>Cancel</button>
          <button
            className="btn btn-p"
            disabled={updateScreen.isPending}
            onClick={save}
          >
            {updateScreen.isPending ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </Modal>
  )
}
