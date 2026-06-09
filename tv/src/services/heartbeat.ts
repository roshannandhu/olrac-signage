import { API_URL } from '../api'

export function startHeartbeat(screenId: string, token: string) {
  const send = () => {
    fetch(`${API_URL}/screens/${screenId}/heartbeat`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` }
    }).catch(() => {}) // Ignore offline errors
  }
  
  send() // Fire immediately
  const id = window.setInterval(send, 30000)
  
  return () => window.clearInterval(id)
}
