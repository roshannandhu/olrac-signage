import { create } from 'zustand'
import type { Group, Media, Screen, Toast, ToastType, Website } from './types'
import { seedMedia, seedScreens, seedWebsites } from './lib/mock'

// Single in-memory store for the mock layer. When the backend lands, each of
// these slices becomes a React Query hook hitting the Olrac API (see plan.md).

let toastSeq = 1

interface State {
  // auth
  authed: boolean
  login: () => void
  logout: () => void

  // data
  media: Media[]
  screens: Screen[]
  groups: Group[]
  websites: Website[]

  // selection (which screen the playlist editor is editing)
  selectedScreen: string

  // toasts
  toasts: Toast[]
  pushToast: (msg: string, type?: ToastType) => void
  dismissToast: (id: number) => void

  // actions
  addMedia: (m: Media) => void
  addScreen: (s: Screen) => void
  selectScreen: (name: string) => void
  addGroup: (g: Group) => void
  removeGroup: (id: string) => void
  addWebsite: (w: Website) => void
}

export const useStore = create<State>((set, get) => ({
  authed: localStorage.getItem('olrac_authed') === '1',
  login: () => {
    localStorage.setItem('olrac_authed', '1')
    set({ authed: true })
  },
  logout: () => {
    localStorage.removeItem('olrac_authed')
    set({ authed: false })
  },

  media: seedMedia,
  screens: seedScreens,
  groups: [],
  websites: seedWebsites,

  selectedScreen: 'Lobby Display',

  toasts: [],
  pushToast: (msg, type = 'success') => {
    const id = toastSeq++
    set((s) => ({ toasts: [...s.toasts, { id, msg, type }] }))
    setTimeout(() => get().dismissToast(id), 3000)
  },
  dismissToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),

  addMedia: (m) => set((s) => ({ media: [m, ...s.media] })),
  addScreen: (sc) => set((s) => ({ screens: [...s.screens, sc] })),
  selectScreen: (name) => set({ selectedScreen: name }),
  addGroup: (g) => set((s) => ({ groups: [...s.groups, g] })),
  removeGroup: (id) => set((s) => ({ groups: s.groups.filter((g) => g.id !== id) })),
  addWebsite: (w) => set((s) => ({ websites: [w, ...s.websites] })),
}))
