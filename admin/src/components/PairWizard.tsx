import { useEffect, useState } from 'react'
import Modal, { ModalHeader } from './Modal'
import { useStore } from '../store'
import { usePairScreen } from '../hooks'
import { enumFromDeg } from '../api'
import type { Screen } from '../types'

// When Supabase is not yet configured we skip the real API and pair locally (demo mode)
const SUPABASE_CONFIGURED =
  !!import.meta.env.VITE_SUPABASE_URL &&
  !(import.meta.env.VITE_SUPABASE_URL as string).includes('YOUR-PROJECT')

type Orient = { label: string; deg: 0 | 90 | 180 | 270 }

const ORIENTS: { label: string; deg: 0 | 90 | 180 | 270; ico: string; flip?: boolean }[] = [
  { label: 'Landscape',        deg: 0,   ico: '🖥️' },
  { label: 'Portrait',         deg: 90,  ico: '📱' },
  { label: 'Upside Down',      deg: 180, ico: '🖥️', flip: true },
  { label: 'Reverse Portrait', deg: 270, ico: '📱', flip: true },
]

function Stepper({ step }: { step: number }) {
  const cls = (n: number) => (step === n ? 'ws active' : step > n ? 'ws done' : 'ws')
  const num = (n: number, label: string) => (
    <div className={cls(n)}>
      <div className="wn">{step > n ? '✓' : n}</div>
      <span>{label}</span>
    </div>
  )
  return (
    <div className="wsteps">
      {num(1, 'Enter code')}
      <div className="wsep" />
      {num(2, 'Orientation')}
      <div className="wsep" />
      {num(3, 'Done')}
    </div>
  )
}

export default function PairWizard({ open, onClose }: { open: boolean; onClose: () => void }) {
  const pushToast = useStore((s) => s.pushToast)
  const addScreen = useStore((s) => s.addScreen)
  const pair = usePairScreen()

  const [step, setStep]     = useState(1)
  const [code, setCode]     = useState('')
  const [name, setName]     = useState('')
  const [orient, setOrient] = useState<Orient>({ label: 'Landscape', deg: 0 })

  // Reset to step 1 every time the modal opens
  useEffect(() => {
    if (open) {
      setStep(1)
      setCode('')
      setName('')
      setOrient({ label: 'Landscape', deg: 0 })
    }
  }, [open])

  const goStep2 = () => {
    if (!code.trim() || code.trim().length < 4) {
      pushToast('Enter a valid pairing code', 'error')
      return
    }
    if (!name.trim()) {
      pushToast('Enter a screen name', 'error')
      return
    }
    setStep(2)
  }

  const goStep3 = () => {
    if (!SUPABASE_CONFIGURED) {
      // Demo mode: mock the pairing locally without a backend
      const screen: Screen = {
        id: `s${Date.now()}`,
        name: name.trim(),
        status: 'online',
        lastSeen: 'Just paired',
        orientLabel: orient.label,
        deg: orient.deg,
      }
      addScreen(screen)
      pushToast(`"${name.trim()}" paired!`, 'success')
      setStep(3)
      return
    }
    pair.mutate(
      { code: code.trim(), name: name.trim(), orientation: enumFromDeg(orient.deg) },
      { onSuccess: () => setStep(3) },
    )
  }

  return (
    <Modal open={open} onClose={onClose}>
      <ModalHeader icon="📺" title="Add screen" onClose={onClose} />

      {/* ── Step 1: Enter code ── */}
      {step === 1 && (
        <div>
          <Stepper step={1} />
          <div className="pair-hint">
            Download the <strong>Olrac Signage</strong> app on your TV. On first launch it shows a pairing
            code — enter it below.
          </div>
          <div className="plat">
            <div className="pb3">🎮 Google Play</div>
            <div className="pb3">📦 Amazon Store</div>
            <div className="pb3">⚡ BrightSign</div>
          </div>
          <div className="fg">
            <label className="fl">Pairing code *</label>
            <input
              className="fi2"
              type="text"
              placeholder="e.g. 483719"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              style={{
                fontFamily: "'JetBrains Mono',monospace",
                fontSize: 22,
                letterSpacing: 5,
                textAlign: 'center',
              }}
            />
          </div>
          <div className="fg">
            <label className="fl">Screen name *</label>
            <input
              className="fi2"
              type="text"
              placeholder="e.g. Lobby Display"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="mf">
            <button className="btn btn-g" onClick={onClose}>Cancel</button>
            <button className="btn btn-p" onClick={goStep2}>Next →</button>
          </div>
        </div>
      )}

      {/* ── Step 2: Orientation picker ── */}
      {step === 2 && (
        <div>
          <Stepper step={2} />
          <p style={{ fontSize: 12.5, color: 'var(--text2)', marginBottom: 14, lineHeight: 1.55 }}>
            Select the physical mounting orientation of this screen. Content will be rotated accordingly.
          </p>
          <div className="og">
            {ORIENTS.map((o) => (
              <div
                key={o.deg}
                className={`oc${orient.deg === o.deg ? ' sel' : ''}`}
                onClick={() => setOrient({ label: o.label, deg: o.deg })}
              >
                <span
                  className="oico"
                  style={o.flip ? { display: 'inline-block', transform: 'rotate(180deg)' } : undefined}
                >
                  {o.ico}
                </span>
                <div className="olbl">{o.label}</div>
                <div className="odeg">+ {o.deg}°</div>
              </div>
            ))}
          </div>
          <div className="mf">
            <button className="btn btn-g" onClick={() => setStep(1)}>← Back</button>
            <button className="btn btn-p" disabled={pair.isPending} onClick={goStep3}>
              {pair.isPending ? 'Pairing…' : 'Pair Screen'}
            </button>
          </div>
        </div>
      )}

      {/* ── Step 3: Done ── */}
      {step === 3 && (
        <div style={{ textAlign: 'center', padding: '8px 0 4px' }}>
          <Stepper step={3} />
          <div style={{ fontSize: 46, margin: '14px 0 9px' }}>✅</div>
          <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text)', marginBottom: 5 }}>
            "{name.trim()}" paired successfully!
          </div>
          <div style={{ fontSize: 12.5, color: 'var(--text3)', marginBottom: 20 }}>
            Orientation: {orient.label} ({orient.deg}°) — content will start playing shortly.
          </div>
          <button className="btn btn-p" onClick={onClose}>Go to Screens</button>
        </div>
      )}
    </Modal>
  )
}
