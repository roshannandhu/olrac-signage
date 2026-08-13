import { create } from 'zustand'
import type { User } from './types'

interface AuthState {
  token: string | null
  user: User | null
  hydrated: boolean
  hydrate: () => void
  setSession: (token: string, user: User) => void
  setUser: (user: User | null) => void
  clearSession: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  hydrated: false,
  hydrate: () => {
    const token = localStorage.getItem('token')
    const rawUser = localStorage.getItem('user')
    let user: User | null = null
    if (rawUser) {
      try {
        user = JSON.parse(rawUser) as User
      } catch {
        localStorage.removeItem('user')
      }
    }
    set({ token, user, hydrated: true })
  },
  setSession: (token, user) => {
    localStorage.setItem('token', token)
    localStorage.setItem('user', JSON.stringify(user))
    set({ token, user })
  },
  setUser: (user) => {
    if (user) localStorage.setItem('user', JSON.stringify(user))
    else localStorage.removeItem('user')
    set({ user })
  },
  clearSession: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    set({ token: null, user: null })
  },
}))
