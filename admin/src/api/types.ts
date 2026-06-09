// Raw API DTOs (snake_case, exactly as FastAPI returns them) + adapters that map
// them to the camelCase UI types in src/types.ts. Pages keep using the UI types;
// only this file knows the wire format.
import type { Group, Media, Screen, Website } from '../types'

// ── Wire enums ──────────────────────────────────────────────────────────
export type OrientationEnum = 'D0' | 'D90' | 'D180' | 'D270'
export type ContentTypeApi = 'video' | 'image'
export type ContentOrient = 'landscape' | 'portrait'
export type ScreenStatusApi = 'pending' | 'online' | 'offline'

// ── DTOs ────────────────────────────────────────────────────────────────
export interface ProfileDTO {
  id: string
  email: string
  name: string
  role: string
}

export interface ContentDTO {
  id: string
  owner_id: string
  name: string
  type: ContentTypeApi
  orientation: ContentOrient
  storage_path: string
  public_url: string
  duration_seconds: number
  file_size: number
  tags: string[]
  start_date: string | null
  expiry_date: string | null
  created_at: string
}

export interface ScreenDTO {
  id: string
  owner_id: string | null
  name: string
  description: string | null
  orientation: OrientationEnum
  status: ScreenStatusApi
  last_seen_at: string | null
  tags: string[]
  created_at: string
}

export interface PlaylistItemDTO {
  id: string
  position: number
  duration_override: number | null
  content: Pick<ContentDTO, 'id' | 'name' | 'type' | 'orientation' | 'public_url' | 'duration_seconds'>
}

export interface GroupDTO {
  id: string
  name: string
  created_at: string
  screens: ScreenDTO[]
  has_playlist: boolean
}

export interface WebsiteDTO {
  id: string
  owner_id: string
  name: string
  url: string
  created_at: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  user: { id: string; email: string; name: string; role: string }
}

// Report rows
export interface SummaryRow {
  content_id: string
  name: string
  type: ContentTypeApi
  screen_count: number
  play_count: number
  total_duration: number
}
export interface ByScreenRow {
  screen_id: string
  screen_name: string
  play_count: number
  total_duration: number
}
export interface HourlyRow {
  screen_id: string
  screen_name: string
  hour: string
  play_count: number
  total_duration: number
}

// ── Orientation helpers (enum ⇄ degrees ⇄ label) ────────────────────────
export const degFromEnum = (o: OrientationEnum): 0 | 90 | 180 | 270 =>
  o === 'D90' ? 90 : o === 'D180' ? 180 : o === 'D270' ? 270 : 0
export const enumFromDeg = (d: number): OrientationEnum =>
  d === 90 ? 'D90' : d === 180 ? 'D180' : d === 270 ? 'D270' : 'D0'
export const labelFromEnum = (o: OrientationEnum): string =>
  o === 'D90' ? 'Portrait' : o === 'D180' ? 'Upside Down' : o === 'D270' ? 'Reverse Portrait' : 'Landscape'

// ── Misc formatting ─────────────────────────────────────────────────────
export function formatDuration(seconds: number): string | null {
  if (!seconds || seconds <= 0) return null
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

export function relativeTime(iso: string | null): string {
  if (!iso) return 'Never'
  const diff = Date.now() - new Date(iso).getTime()
  const s = Math.floor(diff / 1000)
  if (s < 60) return 'Few seconds ago'
  const m = Math.floor(s / 60)
  if (m < 60) return `${m} min ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h} hour${h !== 1 ? 's' : ''} ago`
  const d = Math.floor(h / 24)
  return `${d} day${d !== 1 ? 's' : ''} ago`
}

const BG_BY_TYPE: Record<ContentTypeApi, string> = { video: '#EFF6FF', image: '#F0FDF4' }

// ── Adapters: DTO → UI type ─────────────────────────────────────────────
export function contentToMedia(c: ContentDTO): Media {
  return {
    id: c.id,
    name: c.name,
    type: c.type === 'video' ? 'Video' : 'Image',
    orient: c.orientation,
    dur: c.type === 'video' ? formatDuration(c.duration_seconds) : null,
    ico: c.type === 'video' ? '🎬' : '🖼️',
    bg: BG_BY_TYPE[c.type],
  }
}

export function screenToUi(s: ScreenDTO): Screen {
  return {
    id: s.id,
    name: s.name,
    status: s.status === 'online' ? 'online' : 'offline',
    lastSeen: relativeTime(s.last_seen_at),
    orientLabel: labelFromEnum(s.orientation),
    deg: degFromEnum(s.orientation),
    description: s.description ?? undefined,
  }
}

export function groupToUi(g: GroupDTO): Group {
  return { id: g.id, name: g.name, screens: g.screens.map((s) => s.name) }
}

export function websiteToUi(w: WebsiteDTO): Website {
  return { id: w.id, name: w.name, addedAt: relativeTime(w.created_at) }
}
