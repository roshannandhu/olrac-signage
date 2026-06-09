import { useEffect, useState } from 'react'
import Pairing from './screens/Pairing'
import Connecting from './screens/Connecting'
import Player from './screens/Player'
import Offline from './screens/Offline'

type ScreenState = 'pair' | 'conn' | 'player' | 'offline'

export default function App() {
  // If we already have a token, we might be paired. Jump to connecting to verify.
  const [state, setState] = useState<ScreenState>(() => {
    return localStorage.getItem('screen_token') ? 'conn' : 'pair'
  })

  useEffect(() => {
    if (state !== 'conn') return
    const token = localStorage.getItem('screen_token')
    if (!token) {
      setState('pair')
      return
    }
    
    // Verify token with backend
    import('./api').then(({ fetchMe }) => {
      fetchMe(token)
        .then((data) => {
          if (data.screen.status === 'pending') {
            // Token is for a pending screen that was never paired. Generate a new code.
            localStorage.removeItem('screen_token')
            setState('pair')
          } else {
            // Valid and paired
            setState('player')
          }
        })
        .catch((err) => {
          if (err.isNetworkError) {
            // Offline but we have a token, proceed to player to play cached content
            setState('player')
          } else if (err.status === 401 || err.status === 403 || err.status === 404) {
            // Invalid token -> back to pair
            localStorage.removeItem('screen_token')
            setState('pair')
          } else {
            // Other server errors, maybe just go to player or offline
            setState('player')
          }
        })
    })
  }, [state])

  if (state === 'pair') return <Pairing onPair={() => setState('conn')} />
  if (state === 'conn') return <Connecting />
  if (state === 'offline') return <Offline onRetry={() => setState('conn')} />
  return <Player onExit={() => {
    localStorage.removeItem('screen_token')
    setState('pair')
  }} />
}
