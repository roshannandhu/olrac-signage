import { useEffect, useRef, useState } from 'react'

const DEFAULT_OPTIONS = [
  'Date added (newest)',
  'Date added (oldest)',
  'Alphabetical A–Z',
  'Alphabetical Z–A',
  'Start date',
  'Expiry date',
]

export default function SortMenu({
  options = DEFAULT_OPTIONS,
  onChange,
}: {
  options?: string[]
  onChange?: (option: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(options[0])
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('click', onDoc)
    return () => document.removeEventListener('click', onDoc)
  }, [])

  const select = (o: string) => {
    setActive(o)
    setOpen(false)
    onChange?.(o)
  }

  return (
    <div className="sdd" ref={ref}>
      <button className="btn btn-g btn-sm" onClick={() => setOpen((o) => !o)}>↕ Sort</button>
      {open && (
        <div className="sm open">
          {options.map((o) => (
            <div
              key={o}
              className={`so${active === o ? ' active' : ''}`}
              onClick={() => select(o)}
            >
              {o}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
