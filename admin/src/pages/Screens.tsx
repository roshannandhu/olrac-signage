import { useState } from 'react'
import { useStore } from '../store'
import type { Screen } from '../types'
import { useScreens } from '../hooks'
import ScreenCard from '../components/ScreenCard'
import PairWizard from '../components/PairWizard'
import SettingsModal from '../components/SettingsModal'

export default function Screens() {
  const mockScreens = useStore((s) => s.screens)
  const [showPair, setShowPair] = useState(false)
  const [settingsFor, setSettingsFor] = useState<Screen | null>(null)

  const { data: apiData } = useScreens()
  // Live screens when backend is up; seed from mock otherwise so the UI is always populated
  const screens = apiData ?? mockScreens

  return (
    <div className="page">
      <div className="sh">
        <span className="sh-t">Screens</span>
        <div className="tb">
          <button className="btn btn-g btn-sm">↕ Sort</button>
          <button className="btn btn-p btn-sm" onClick={() => setShowPair(true)}>+ Add Screen</button>
        </div>
      </div>

      <div className="sg">
        {screens.map((s) => (
          <ScreenCard key={s.id} s={s} onSettings={setSettingsFor} />
        ))}
      </div>

      <PairWizard open={showPair} onClose={() => setShowPair(false)} />
      <SettingsModal
        open={settingsFor !== null}
        onClose={() => setSettingsFor(null)}
        screen={settingsFor ?? undefined}
      />
    </div>
  )
}
