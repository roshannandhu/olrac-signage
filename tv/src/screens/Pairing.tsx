import { useEffect, useState } from 'react'
import { requestPairingCode, fetchMe } from '../api'

const USE_PROD_API = true

export default function Pairing({ onPair }: { onPair: () => void }) {
  const [code, setCode] = useState<string[]>(['-', '-', '-', '-', '-', '-'])
  const [error, setError] = useState('')

  useEffect(() => {
    if (!USE_PROD_API) {
      setCode(['4', '8', '3', '7', '1', '9'])
      return
    }

    let isMounted = true
    let pollInterval: number

    async function initPairing() {
      try {
        const { code: newCode, screen_token } = await requestPairingCode()
        if (!isMounted) return
        setCode(newCode.split(''))
        setError('')
        localStorage.setItem('screen_token', screen_token)

        pollInterval = window.setInterval(async () => {
          try {
            const data = await fetchMe(screen_token)
            if (data.screen.status !== 'pending') {
              // The screen was paired by an admin
              clearInterval(pollInterval)
              onPair()
            }
          } catch (err: any) {
            // If the code expired or was rejected, we get an error. Re-request.
            if (err.message.includes('code') || err.message.includes('not found')) {
              clearInterval(pollInterval)
              initPairing()
            }
          }
        }, 5000)
      } catch (err: any) {
        console.error("PAIRING ERROR:", err)
        if (isMounted) setError(`Failed: ${err?.message || 'unknown error'}. Retrying...`)
        setTimeout(initPairing, 5000)
      }
    }

    initPairing()

    return () => {
      isMounted = false
      if (pollInterval) clearInterval(pollInterval)
    }
  }, [onPair])

  return (
    <div className="scr scr-pair">
      <div className="pair-bg-lines" />
      <div className="pair-card">
        <div className="brand-row">
          <div className="brand-icon">📺</div>
          <div className="brand-col">
            <div className="brand-name">Olrac Signage</div>
            <div className="brand-sub">Digital Display System</div>
          </div>
        </div>
        <div className="pair-lbl">Pairing Code</div>
        <div className="pair-code">
          <div className="pd">{code[0]}</div>
          <div className="pd">{code[1]}</div>
          <div className="pd">{code[2]}</div>
          <div className="psep" />
          <div className="pd">{code[3]}</div>
          <div className="pd">{code[4]}</div>
          <div className="pd">{code[5]}</div>
        </div>
        <div className="pair-inst">
          Enter this code in <strong>Olrac Signage Admin</strong>
          <br />
          Go to <strong>Screens → Add Screen</strong> and type the code above.
          <br />
          Code refreshes every <strong>10 minutes</strong>.
          {error && <div style={{ color: 'var(--red)', marginTop: 8 }}>{error}</div>}
        </div>
        <div className="pair-plat">
          <div className="pp">🎮 Google Play</div>
          <div className="pp">📦 Amazon Store</div>
          <div className="pp">⚡ BrightSign</div>
        </div>
        {!USE_PROD_API && (
          <button className="pair-btn" onClick={onPair}>
            ▶ Simulate Pairing (Demo)
          </button>
        )}
      </div>
    </div>
  )
}
