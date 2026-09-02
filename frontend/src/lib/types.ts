/**
 * `super_admin` is the platform operator, not a tenant role. It is the only role that may
 * publish or promote a player release, because a release installs across every tenant's
 * fleet. The team page never offers it — TenantRole is what that page may assign.
 */
export type Role = 'super_admin' | 'manager' | 'owner' | 'editor' | 'viewer'
export type TenantRole = 'manager' | 'owner' | 'editor' | 'viewer'
/** Promotion ring for a player build. Only `released` reaches screens with no pin. */
export type RolloutState = 'draft' | 'canary' | 'released'
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
  organization_status?: string | null
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

  // 1:1 Unified Ad & Client metadata
  client_id?: number | null
  client_name?: string | null
  client_email?: string | null
  client_phone?: string | null
  plan_id?: number | null
  plan_name?: string | null
  placement_id?: number | null
  placement_status?: string | null
  placement_price_paise?: number | null
  placement_starts_at?: string | null
  placement_ends_at?: string | null
  placement_notes?: string | null
  screen_ids?: number[]
  // Per-location run lengths, keyed by screen id. Absent means every location runs the
  // booking's own window, which is the ordinary sale.
  screen_days?: Record<number, number>
  screen_names?: string[]
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
  rollout_state: RolloutState
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

/** What a tenant puts at the top of the report they hand their client. */
export interface Branding {
  brand_name: string | null
  brand_color: string | null
  /** Already resolved for display; the column holds the host-independent form. */
  logo_url: string | null
  /** What the report actually prints, once the workspace-name fallback is applied. */
  effective_name: string
}

/** An advertiser this tenant sells to. Reusable across bookings, unlike a typed-in name. */
export interface Client {
  id: number
  name: string
  client_code: string
  email: string | null
  phone: string | null
  notes: string | null
  active_campaigns_count?: number
  total_spent_paise?: number
  created_at: string
}

/** A package the tenant sells on to its clients — not the plan OLRAC bills the tenant. */
export interface TenantPlan {
  id: number
  name: string
  description: string | null
  duration_days: number
  max_locations: number
  ad_slots: number
  price_paise: number
  support_tier: string
  is_active: boolean
  created_at: string
}

/** One paid extension of a booking's run. A booking may have several. */
export interface PlacementExtension {
  id: number
  extended_from: string
  extended_to: string
  additional_price_paise: number
  is_paid: boolean
  notes: string | null
  created_at: string
}

/** An advert sold to a client: who, how long, where, and for how much. */
export interface Placement {
  id: number
  content_id: number
  creative_name?: string | null
  creative_thumbnail_url?: string | null
  advertiser: string
  client: Client | null
  plan: TenantPlan | null
  extensions: PlacementExtension[]
  /** Where the run actually finishes once extensions count. `ends_at` stays as sold. */
  effective_ends_at: string | null
  days_remaining?: number | null
  /** The booking plus every extension sold against it. */
  total_price_paise: number | null
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

export type AlertSeverity = 'critical' | 'warning'

export interface FleetAlert {
  id: number
  kind: string
  severity: AlertSeverity
  title: string
  detail: string | null
  screen_id: number | null
  content_id: number | null
  raised_at: string
  resolved_at: string | null
  acknowledged_at: string | null
}

export interface AlertSummary {
  total: number
  critical: number
  warning: number
  unacknowledged: number
}

// --- Platform administration ---------------------------------------------------------
// Mirrors the Pydantic models in backend/routers/admin.py. These are cross-tenant shapes
// only a super_admin can fetch, kept apart from the tenant types above for that reason.

export interface TenantSummary {
  id: number
  name: string
  slug: string
  status: string
  created_at: string
  owner_email?: string | null
  owner_name?: string | null
  plan_id?: number | null
  plan_name?: string | null
  screens_count: number
  online_screens_count: number
  // null = no limit configured; 0 = a package that grants none. Rendered differently, so
  // `max_screens || '∞'` is wrong here -- it would show a zero-screen package as unlimited.
  max_screens: number | null
  max_ad_slots: number | null
  // The raw override the quota dialog edits; 0 = "no override, follow the package".
  max_screens_override: number
  max_ad_slots_override: number
  ad_slots_used: number
  storage_used_bytes: number
  storage_quota_bytes: number
  rejection_reason?: string | null
}

export interface TenantScreen {
  id: number
  name?: string | null
  status: string
  last_seen?: string | null
  location?: string | null
  model?: string | null
  app_version?: string | null
  playback_state: string
}

export interface TenantContent {
  id: number
  name?: string | null
  type?: string | null
  status: string
  file_size_bytes: number
  uploaded_at?: string | null
  thumbnail?: string | null
}

export interface TenantUser {
  id: number
  username: string
  email?: string | null
  full_name?: string | null
  role: string
  is_active: boolean
}

export interface Package {
  id: number
  name: string
  slug: string
  monthly_price_paise: number
  yearly_price_paise: number
  max_screens: number
  max_storage_bytes: number
  max_ad_slots: number
  is_active: boolean
}

// slug is write-once: /api/billing/checkout resolves the payment provider's plan id from
// an env var named after it, so renaming one silently breaks checkout for that package.
export interface PackageWrite {
  name: string
  slug: string
  monthly_price_paise: number
  yearly_price_paise: number
  max_screens: number
  max_storage_bytes: number
  max_ad_slots: number
  is_active: boolean
}
