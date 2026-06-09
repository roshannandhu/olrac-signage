import { API_URL } from '../api'

export interface LogEntry {
  content_id: string
  played_at: string
  duration_played: number
}

const STORAGE_KEY = 'olrac_pending_logs'

export class PlaybackLogger {
  private queue: LogEntry[] = []
  private token: string
  private intervalId: number

  constructor(token: string) {
    this.token = token
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) this.queue = JSON.parse(stored)
    } catch {}

    // Flush every 60s
    this.intervalId = window.setInterval(() => this.flush(), 60000)
  }

  log(entry: LogEntry) {
    this.queue.push(entry)
    this.save()
    if (this.queue.length >= 20) {
      this.flush()
    }
  }

  private save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(this.queue))
  }

  async flush() {
    if (this.queue.length === 0) return
    const batch = [...this.queue]
    
    try {
      const res = await fetch(`${API_URL}/playback/log`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${this.token}`
        },
        body: JSON.stringify(batch)
      })
      
      if (res.ok) {
        // Remove successfully sent items from queue
        this.queue = this.queue.filter(e => !batch.includes(e))
        this.save()
      }
    } catch {
      // Offline: keep in queue for next flush
    }
  }

  destroy() {
    window.clearInterval(this.intervalId)
    this.flush()
  }
}
