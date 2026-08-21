export type Role = 'owner' | 'editor' | 'viewer'
export type TransitionName = 'none' | 'fade' | 'slide_left' | 'slide_right' | 'slide_up' | 'slide_down' | 'zoom'

export interface User {
  id: number
  organization_id: number
  username: string
  role: Role
  is_active: boolean
  created_at: string
  full_name?: string | null
  email?: string | null
  organization_name?: string | null
}

export interface ContentItem {
  id: number
  type: 'image' | 'video' | 'website'
  file_url: string
  thumbnail: string | null
  name: string
  tags: string | null
  uploaded_at: string
  file_size_bytes: number
  expires_at: string | null
  status: 'processing' | 'ready' | 'failed'
  failed_reason: string | null
  duration_ms?: number | null
  renditions?: MediaRendition[]
}

export interface MediaRendition {
  id: number
  resolution: string
  width: number
  height: number
  rotation: number
  duration_ms: number | null
  codec: string | null
  sha256: string | null
  file_size_bytes: number
  file_url: string
}

export interface EnrollmentToken {
  id: number
  token: string | null
  description: string | null
  created_at: string
  expires_at: string | null
  max_uses: number | null
  use_count: number
  is_active: boolean
}

export interface ItemSchedule {
  id?: number
  days_of_week: number[]
  start_time: string | null
  end_time: string | null
}

export interface PlaylistItem {
  id: number
  content_id: number
  duration: number
  /** null = follow the screen's own orientation. */
  rotation: number | null
  order: number
  start_at: string | null
  end_at: string | null
  transition: TransitionName | null
  transition_ms: number | null
  schedule: ItemSchedule | null
  content: ContentItem
}

export interface Playlist {
  id: number
  name: string
  default_transition: TransitionName
  default_transition_ms: number
  created_at: string
  updated_at: string
  items: PlaylistItem[]
}

export interface Screen {
  id: number
  device_id: string | null
  pair_code: string | null
  name: string | null
  orientation: number
  status: 'online' | 'offline' | 'waiting_pairing'
  last_seen: string
  playlist_id: number | null
  group_id: number | null
  device_version: string | null
  app_version: string | null
  storage_used: string | null
  playback_state: 'playing' | 'idle' | 'error'
  current_item_id: number | null
  last_error: string | null
  last_error_at: string | null
  effective_playlist_id: number | null
  orientation_source?: 'auto' | 'manual'
  latest_screenshot?: string | null
  description?: string | null
  tags?: string | null
  location?: string | null
  latitude?: number | null
  longitude?: number | null
  place_id?: string | null
  fit_mode?: FitMode
  /** Unlocks the player's on-TV maintenance screen. Four digits, per screen. */
  maintenance_pin?: string | null
  sync_playback?: boolean
  sync_role?: SyncRole
  leader_screen_id?: number | null
  operating_mode?: OperatingMode
  operating_hours?: Record<string, [string, string]> | null
  target_version_code: number | null
  update_status: string | null  // pending | downloading | installing | success | failed
  screen_width: number | null
  screen_height: number | null
  refresh_rate: number | null
  total_ram_mb: number | null
  available_ram_mb: number | null
  total_storage_mb: number | null
  free_storage_mb: number | null
  supported_video_codecs: string[] | null
  max_decode_width: number | null
  max_decode_height: number | null
  manufacturer: string | null
  model: string | null
  android_version: string | null
  sdk_int: number | null
  network_type: string | null
  timezone: string | null
}

export interface ScreenGroup {
  id: number
  name: string
  playlist_id: number | null
  created_at: string
  updated_at: string
  screen_count: number
}

export interface Plan {
  id: number
  name: string
  slug: string
  monthly_price_paise: number
  yearly_price_paise: number
  max_screens: number
  max_storage_bytes: number
  feature_flags: Record<string, boolean>
}

export interface Subscription {
  status: string
  billing_period: 'monthly' | 'yearly'
  current_period_start: string | null
  current_period_end: string | null
  grace_period_end: string | null
  provider: string | null
  provider_subscription_id: string | null
}

export interface BillingSummary {
  plan: Plan
  subscription: Subscription
  screens_used: number
  storage_used_bytes: number
  is_read_only: boolean
}

export interface CheckoutSession {
  provider: string
  provider_subscription_id: string
  checkout_url: string
}

export interface AppRelease {
  id: number
  version_code: number
  version_name: string
  apk_url: string
  sha256: string | null
  mandatory: boolean
  created_at: string
}

export interface EmergencyBroadcast {
  id: number
  target_type: 'all' | 'group' | 'screen'
  target_id: number | null
  playlist_id: number
  updated_at: string
}

export type CampaignExportFormat = 'csv' | 'excel' | 'pdf'

export interface Campaign {
  id: number
  name: string
}

export interface CampaignInfo extends Campaign {
  assigned_screens: number
  online: number
  offline: number
  currently_playing: number
}

export interface CampaignPeriodStats {
  total_plays: number
  success_percent: number
}

export interface CampaignStats {
  today: CampaignPeriodStats
  yesterday: CampaignPeriodStats
  week: CampaignPeriodStats
  lifetime: CampaignPeriodStats
}

export interface CampaignPoint {
  date: string
  total_plays: number
  completed_plays: number
}

export interface Screenshot {
  id: number
  screen_id: number
  url: string
  created_at: string
}

/** How the player handles content whose aspect ratio differs from the panel. */
export type FitMode = 'contain' | 'cover'
/** Video-wall role: a follower takes its playback clock from its leader. */
export type SyncRole = 'leader' | 'follower'
export type OperatingMode = 'always' | 'hours' | 'never'

export const WEEKDAYS = [
  { key: 'mon', label: 'Monday' },
  { key: 'tue', label: 'Tuesday' },
  { key: 'wed', label: 'Wednesday' },
  { key: 'thu', label: 'Thursday' },
  { key: 'fri', label: 'Friday' },
  { key: 'sat', label: 'Saturday' },
  { key: 'sun', label: 'Sunday' },
] as const

export interface MediaPeriodStats {
  total_plays: number
  completed_plays: number
  error_plays: number
  success_percent: number
}

export interface MediaScreenRow {
  screen_id: number
  screen_name: string
  group_name: string | null
  location: string | null
  latitude: number | null
  longitude: number | null
  total_plays: number
  completed_plays: number
  error_plays: number
  last_played: string | null
}

export interface MediaLocationRow {
  /** The screen's real location, falling back to its group name when unset. */
  location: string
  screens: number
  total_plays: number
  completed_plays: number
}

/** Proof-of-play for a single advert, from the deduplicated hourly rollups. */
export interface MediaReport {
  content_id: number
  today: MediaPeriodStats
  week: MediaPeriodStats
  month: MediaPeriodStats
  lifetime: MediaPeriodStats
  per_screen: MediaScreenRow[]
  per_location: MediaLocationRow[]
  daily: { date: string; total_plays: number; completed_plays: number }[]
}

export interface PlacementTarget {
  id: number
  screen_id: number | null
  group_id: number | null
  name: string
  kind: 'screen' | 'group'
  /** False if the playlist item was deleted by hand — sold, but no longer on air there. */
  is_placed: boolean
}

/** An advert sold to a client: who, how long, where, and for how much. */
export interface Placement {
  id: number
  content_id: number
  advertiser: string
  price_paise: number
  is_paid: boolean
  starts_at: string
  ends_at: string
  notes: string | null
  created_at: string
  targets: PlacementTarget[]
}

export interface BookingReportScreen {
  screen_id: number
  screen_name: string
  location: string | null
  latitude: number | null
  longitude: number | null
  online: boolean
  last_seen: string | null
  total_plays: number
  completed_plays: number
  /** The screen has not reported recently, so this figure may still rise. */
  counts_may_be_incomplete: boolean
}

/** Proof of delivery for one booking: only its window, only its screens. */
export interface BookingReport {
  placement_id: number
  advertiser: string
  content_name: string
  content_id: number
  starts_at: string
  ends_at: string
  price_paise: number
  is_paid: boolean
  generated_at: string
  totals: { total_plays: number; completed_plays: number; error_plays: number; success_percent: number }
  per_screen: BookingReportScreen[]
  per_location: { location: string; screens: number; total_plays: number }[]
  daily: { date: string; total_plays: number }[]
  stale_screens: string[]
}
