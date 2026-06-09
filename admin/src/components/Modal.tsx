import type { ReactNode } from 'react'

interface ModalProps {
  open: boolean
  onClose: () => void
  small?: boolean
  children: ReactNode
}

// Overlay + card. Clicking the dimmed backdrop closes; clicking the card does not.
export default function Modal({ open, onClose, small, children }: ModalProps) {
  return (
    <div
      className={`mo${open ? ' open' : ''}`}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className={`md${small ? ' md-sm' : ''}`}>{children}</div>
    </div>
  )
}

export function ModalHeader({ icon, title, onClose }: { icon: string; title: string; onClose: () => void }) {
  return (
    <div className="mh">
      <div className="mi2">{icon}</div>
      <div className="mt">{title}</div>
      <button className="mc2" onClick={onClose}>✕</button>
    </div>
  )
}
