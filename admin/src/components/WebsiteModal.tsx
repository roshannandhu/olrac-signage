import { useState } from 'react'
import Modal, { ModalHeader } from './Modal'
import { useStore } from '../store'
import { useAddWebsite } from '../hooks/useWebsites'

export default function WebsiteModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { pushToast } = useStore()
  const { mutate: addWebsite } = useAddWebsite()
  
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')

  const submit = () => {
    if (!name.trim()) {
      pushToast('Please enter a website name', 'error')
      return
    }

    let validUrl = false
    try {
      const u = new URL(url.trim())
      validUrl = u.protocol === 'http:' || u.protocol === 'https:'
    } catch {
      validUrl = false
    }

    if (!validUrl) {
      pushToast('Please enter a valid http(s) URL', 'error')
      return
    }

    addWebsite({ name: name.trim(), url: url.trim() })
    setName('')
    setUrl('')
    onClose()
  }

  return (
    <Modal open={open} onClose={onClose} small>
      <ModalHeader icon="🌐" title="Add website" onClose={onClose} />
      <div className="fg">
        <label className="fl">Website name *</label>
        <input className="fi2" type="text" placeholder="e.g. Company dashboard" value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <div className="fg">
        <label className="fl">URL *</label>
        <input className="fi2" type="url" placeholder="https://…" value={url} onChange={(e) => setUrl(e.target.value)} />
      </div>
      <div className="mf">
        <button className="btn btn-g" onClick={onClose}>Cancel</button>
        <button className="btn btn-p" onClick={submit}>Add Website</button>
      </div>
    </Modal>
  )
}
