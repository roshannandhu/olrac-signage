export type Role = 'owner' | 'editor' | 'viewer'
export type TransitionName = 'none' | 'fade' | 'slide_left' | 'slide_right' | 'slide_up' | 'slide_down' | 'zoom'

export interface User {
  id: number
  organization_id: number
  username: string
  role: Role
  is_active: boolean
  created_at: string
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
  last_version_code: number | null
  target_version_code: number | null
  update_status: string | null
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
