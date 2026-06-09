// Shared domain types. These mirror the backend data model in plan.md so the
// mock layer can later be swapped for the real Olrac API with minimal changes.

export type MediaType = 'Video' | 'Image'
export type MediaOrient = 'landscape' | 'portrait'

export interface Media {
  id: string
  name: string
  type: MediaType
  orient: MediaOrient
  dur: string | null // e.g. "0:20" for video, null for image
  ico: string // emoji placeholder thumbnail
  bg: string // thumbnail background colour
}

export type ScreenStatus = 'online' | 'offline'

export interface Screen {
  id: string
  name: string
  status: ScreenStatus
  lastSeen: string
  orientLabel: string // Landscape | Portrait | Upside Down | Reverse Portrait
  deg: 0 | 90 | 180 | 270
  description?: string
}

export interface Group {
  id: string
  name: string
  screens: string[] // screen names assigned to the group
}

export interface Website {
  id: string
  name: string
  addedAt: string
}

export type ToastType = 'success' | 'error'

export interface Toast {
  id: number
  msg: string
  type: ToastType
}
