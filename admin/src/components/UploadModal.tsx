import { useRef, useState } from 'react'
import Modal, { ModalHeader } from './Modal'
import { useUploadContent } from '../hooks'

export default function UploadModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const upload = useUploadContent()
  const fileRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return
    Array.from(files).forEach((file) => upload.mutate({ file }))
    if (fileRef.current) fileRef.current.value = ''
    onClose()
  }

  return (
    <Modal open={open} onClose={onClose}>
      <ModalHeader icon="⬆️" title="Upload files" onClose={onClose} />
      <div
        className={`dz${dragOver ? ' dov' : ''}`}
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragOver(false)
          handleFiles(e.dataTransfer.files)
        }}
      >
        <div className="dz-ico">⬆</div>
        <div className="dz-t">Drag and drop media files here</div>
        <div className="dz-h">Supports MP4, MOV, JPG, PNG · Max 500 MB</div>
      </div>
      <input
        ref={fileRef}
        type="file"
        style={{ display: 'none' }}
        multiple
        accept="video/*,image/*"
        onChange={(e) => handleFiles(e.target.files)}
      />
      <div className="mf" style={{ marginTop: 12 }}>
        <button className="btn btn-g" onClick={onClose}>Cancel</button>
        <button
          className="btn btn-p"
          disabled={upload.isPending}
          onClick={() => handleFiles(fileRef.current?.files ?? null)}
        >
          {upload.isPending ? 'Uploading…' : 'Upload'}
        </button>
      </div>
    </Modal>
  )
}
