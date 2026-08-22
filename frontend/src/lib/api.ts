import { useAuthStore } from './store'
import type { AlertSummary, FleetAlert, BookingReport, Placement, MediaReport, FitMode, OperatingMode, RolloutState, SyncRole, AppRelease, BillingSummary, Campaign, CampaignExportFormat, CampaignInfo, CampaignPoint, CampaignStats, CheckoutSession, ContentItem, EmergencyBroadcast, EnrollmentToken, ItemSchedule, Plan, Playlist, Screen, TenantRole, ScreenGroup, Screenshot, TransitionName, User } from './types'

const configuredUrl = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '')
let API_BASE = `${configuredUrl}/api`

// If accessed on a mobile device over the local network, replace localhost with the actual IP.
if (typeof window !== 'undefined') {
  try {
    const url = new URL(API_BASE)
    if (url.hostname === 'localhost' || url.hostname === '127.0.0.1') {
      url.hostname = window.location.hostname
      API_BASE = url.href.replace(/\/$/, '')
    }
  } catch {
    // A malformed NEXT_PUBLIC_API_URL just means we keep the configured value.
  }
}

export const WS_BASE = API_BASE.replace(/^http/, 'ws')

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message)
  }
}

async function authFetch(endpoint: string, options: RequestInit = {}): Promise<Response> {
  const token = useAuthStore.getState().token
  const headers = new Headers(options.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers })
  if (response.status === 401) {
    useAuthStore.getState().clearSession()
    if (typeof window !== 'undefined') window.location.assign('/login')
    throw new ApiError('Your session has expired', 401)
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    const detail = typeof payload?.detail === 'string' ? payload.detail : 'Something went wrong'
    throw new ApiError(detail, response.status)
  }
  return response
}

async function fetchWithAuth<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const response = await authFetch(endpoint, options)
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  login: async (username: string, password: string) => {
    const response = await fetch(`${API_BASE}/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ username, password }),
    })
    if (!response.ok) throw new ApiError('The username or password is incorrect', response.status)
    return response.json() as Promise<{ access_token: string; token_type: string; user: User }>
  },
  me: () => fetchWithAuth<User>('/auth/me'),
  updateProfile: (data: { full_name?: string | null; email?: string | null }) =>
    fetchWithAuth<User>('/auth/me', {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
    }),
  changePassword: (data: { current_password: string; new_password: string }) =>
    fetchWithAuth<void>('/auth/change-password', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
    }),
  getScreens: () => fetchWithAuth<Screen[]>('/screens/'),
  resolveLocationLink: (link: string) =>
    fetchWithAuth<{ latitude: number; longitude: number; name: string | null }>(
      '/screens/resolve-location-link',
      { method: 'POST', body: JSON.stringify({ link }) },
    ),
  // Partial by design: sending only the edited keys stops a rename from resetting
  // orientation, which is not editable anywhere in the dashboard.
  patchScreen: (id: number, data: Partial<{
    name: string
    orientation: number
    group_id: number | null
    target_version_code: number | null
    description: string | null
    tags: string | null
    location: string | null
    latitude: number | null
    longitude: number | null
    place_id: string | null
    timezone: string | null
    fit_mode: FitMode
    /** Four digits. The API rejects any other shape. */
    maintenance_pin: string
    sync_playback: boolean
    sync_role: SyncRole
    leader_screen_id: number | null
    operating_mode: OperatingMode
    operating_hours: Record<string, [string, string]> | null
  }>) => fetchWithAuth<Screen>(`/screens/${id}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }),
  pairScreen: (pairCode: string) => fetchWithAuth<Screen>('/screens/pair', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pair_code: pairCode }),
  }),
  revokeScreenDeviceSecret: (screenId: number) => fetchWithAuth(`/screens/${screenId}/device-secret`, { method: 'DELETE' }),
  assignPlaylist: (screenId: number, playlistId: number) =>
    fetchWithAuth(`/screens/${screenId}/assign/${playlistId}`, { method: 'POST' }),
  clearScreenAssignment: (screenId: number) =>
    fetchWithAuth(`/screens/${screenId}/assign`, { method: 'DELETE' }),

  getGroups: () => fetchWithAuth<ScreenGroup[]>('/groups/'),
  createGroup: (name: string) => fetchWithAuth<ScreenGroup>('/groups/', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }),
  }),
  setGroupScreens: (groupId: number, screenIds: number[]) => fetchWithAuth<ScreenGroup>(`/groups/${groupId}/screens`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ screen_ids: screenIds }),
  }),
  assignGroupPlaylist: (groupId: number, playlistId: number) =>
    fetchWithAuth<ScreenGroup>(`/groups/${groupId}/assign/${playlistId}`, { method: 'POST' }),
  renameGroup: (groupId: number, name: string) => fetchWithAuth<ScreenGroup>(`/groups/${groupId}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }),
  }),
  deleteGroup: (groupId: number) => fetchWithAuth<{ status: string }>(`/groups/${groupId}`, { method: 'DELETE' }),

  getContent: () => fetchWithAuth<ContentItem[]>('/content/'),
  getMediaReport: (contentId: number) => fetchWithAuth<MediaReport>(`/analytics/media/${contentId}`),
  // Uses XHR rather than fetch purely for upload progress: fetch cannot report it, and a
  // several-hundred-megabyte advert otherwise sits on "uploading" for minutes with no sign
  // of life. Error and 401 handling mirror authFetch.
  uploadContent: (file: File, name: string, tags: string, onProgress?: (percent: number) => void) =>
    new Promise<ContentItem>((resolve, reject) => {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('name', name)
      if (tags.trim()) formData.append('tags', tags)

      const request = new XMLHttpRequest()
      request.open('POST', `${API_BASE}/content/upload`)
      const token = useAuthStore.getState().token
      if (token) request.setRequestHeader('Authorization', `Bearer ${token}`)

      request.upload.onprogress = (event) => {
        if (event.lengthComputable) onProgress?.(Math.round((event.loaded / event.total) * 100))
      }
      request.onload = () => {
        if (request.status === 401) {
          useAuthStore.getState().clearSession()
          if (typeof window !== 'undefined') window.location.assign('/login')
          reject(new ApiError('Your session has expired', 401))
          return
        }
        if (request.status >= 200 && request.status < 300) {
          try {
            resolve(JSON.parse(request.responseText) as ContentItem)
          } catch {
            reject(new ApiError('The server returned an unreadable response', request.status))
          }
          return
        }
        let detail = 'Something went wrong'
        try {
          const payload = JSON.parse(request.responseText)
          if (typeof payload?.detail === 'string') detail = payload.detail
        } catch {
          // keep the generic message
        }
        reject(new ApiError(detail, request.status))
      }
      request.onerror = () => reject(new ApiError('The upload could not reach the server', 0))
      request.send(formData)
    }),
  deleteContent: (id: number) => fetchWithAuth(`/content/${id}`, { method: 'DELETE' }),
  retryContentProcessing: (id: number) => fetchWithAuth<ContentItem>(`/content/${id}/retry`, { method: 'POST' }),

  generateProvisioningQr: (data: {
    wifi_ssid: string
    wifi_password: string
    wifi_security_type: string
    max_uses: number
  }) => fetchWithAuth<Record<string, unknown>>('/provisioning/qr', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }),

  getBookingReport: (placementId: number) => fetchWithAuth<BookingReport>(`/placements/${placementId}/report`),
  bookingReportPdfUrl: (placementId: number) => `${API_BASE}/placements/${placementId}/report.pdf`,
  getPlacements: (contentId: number) => fetchWithAuth<Placement[]>(`/placements/?content_id=${contentId}`),
  createPlacement: (data: {
    content_id: number
    advertiser: string
    price_paise: number
    is_paid: boolean
    starts_at: string
    ends_at: string
    notes?: string | null
    targets: { screen_id?: number; group_id?: number }[]
  }) => fetchWithAuth<Placement>('/placements/', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }),
  updatePlacement: (id: number, data: Partial<{
    advertiser: string; price_paise: number; is_paid: boolean
    starts_at: string; ends_at: string; notes: string | null
  }>) => fetchWithAuth<Placement>(`/placements/${id}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }),
  addPlacementTarget: (id: number, target: { screen_id?: number; group_id?: number }) =>
    fetchWithAuth<Placement>(`/placements/${id}/targets`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(target),
    }),
  removePlacementTarget: (id: number, targetId: number) =>
    fetchWithAuth<Placement>(`/placements/${id}/targets/${targetId}`, { method: 'DELETE' }),
  splitPlacementTarget: (id: number, targetId: number, excludeScreenIds: number[]) =>
    fetchWithAuth<Placement>(`/placements/${id}/targets/${targetId}/split`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ exclude_screen_ids: excludeScreenIds }),
    }),
  deletePlacement: (id: number) => fetchWithAuth(`/placements/${id}`, { method: 'DELETE' }),

  getEnrollmentTokens: () => fetchWithAuth<EnrollmentToken[]>('/enrollment-tokens/'),
  createEnrollmentToken: (data: { description?: string, expires_at?: string, max_uses?: number }) => 
    fetchWithAuth<EnrollmentToken>('/enrollment-tokens/', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data)
    }),
  revokeEnrollmentToken: (id: number) => fetchWithAuth(`/enrollment-tokens/${id}`, { method: 'DELETE' }),

  getPlaylists: () => fetchWithAuth<Playlist[]>('/playlists/'),
  createPlaylist: (name: string) => fetchWithAuth<Playlist>('/playlists/', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }),
  }),
  getPlaylist: (id: number) => fetchWithAuth<Playlist>(`/playlists/${id}`),
  reorderPlaylistItems: (id: number, orders: number[]) => fetchWithAuth(`/playlists/${id}/items/reorder`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(orders),
  }),
  // duration is deliberately omitted: the server defaults a video to its real length
  // (from ffprobe) and only falls back to 10s for images. Sending 10 here would
  // truncate every advert longer than ten seconds.
  addPlaylistItem: (id: number, contentId: number, order: number) => fetchWithAuth(`/playlists/${id}/items`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content_id: contentId, order }),
  }),
  updatePlaylistItem: (playlistId: number, itemId: number, data: Partial<{
    duration: number
    rotation: number | null
    start_at: string | null
    end_at: string | null
    schedule: Omit<ItemSchedule, 'id'> | null
    transition: TransitionName | null
    transition_ms: number | null
  }>) => fetchWithAuth(`/playlists/${playlistId}/items/${itemId}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }),
  updatePlaylistTransitions: (playlistId: number, data: { transition: TransitionName; transition_ms: number; apply_to_all: boolean }) =>
    fetchWithAuth<Playlist>(`/playlists/${playlistId}/transitions`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
    }),
  removePlaylistItem: (playlistId: number, itemId: number) =>
    fetchWithAuth(`/playlists/${playlistId}/items/${itemId}`, { method: 'DELETE' }),

  getUsers: () => fetchWithAuth<User[]>('/users/'),
  // TenantRole, not Role: the API refuses to create a platform account here, so the
  // type should not let the dashboard try.
  createUser: (data: { username: string; password: string; role: TenantRole }) => fetchWithAuth<User>('/users/', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }),
  updateUser: (id: number, data: { role?: TenantRole; is_active?: boolean }) => fetchWithAuth<User>(`/users/${id}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }),

  getBillingSummary: () => fetchWithAuth<BillingSummary>('/billing/summary'),
  getPlans: () => fetchWithAuth<Plan[]>('/billing/plans'),
  createCheckout: (planId: number, billingPeriod: 'monthly' | 'yearly') => fetchWithAuth<CheckoutSession>('/billing/checkout', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ plan_id: planId, billing_period: billingPeriod }),
  }),

  // P6/P7 Endpoints
  getEmergencyBroadcasts: () => fetchWithAuth<EmergencyBroadcast[]>('/emergency/active'),
  triggerEmergencyBroadcast: (data: { target_type: string, target_id: number | null, playlist_id: number }) =>
    fetchWithAuth('/emergency/broadcast', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),
  cancelEmergencyBroadcast: (data: { target_type: string, target_id: number | null, playlist_id: number }) =>
    fetchWithAuth('/emergency/broadcast', { method: 'DELETE', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),
    
  getScreenshots: (screenId: number) => fetchWithAuth<Screenshot[]>(`/screenshots/${screenId}/screenshots`),
  requestScreenshot: (screenId: number) => fetchWithAuth(`/screenshots/${screenId}/request-screenshot`, { method: 'POST' }),

  getCampaigns: () => fetchWithAuth<Campaign[]>('/analytics/campaigns'),
  getCampaign: (id: number) => fetchWithAuth<CampaignInfo>(`/analytics/campaigns/${id}`),
  getCampaignStats: (id: number) => fetchWithAuth<CampaignStats>(`/analytics/campaigns/${id}/stats`),
  getCampaignTimeseries: (id: number) => fetchWithAuth<CampaignPoint[]>(`/analytics/campaigns/${id}/timeseries`),
  // The export endpoint authenticates by header like every other route, so it cannot
  // be reached by navigating to a ?token= URL: that 401s and leaks the JWT into history.
  downloadCampaignReport: async (id: number, format: CampaignExportFormat) => {
    const response = await authFetch(`/analytics/campaigns/${id}/export?format=${format}`)
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `campaign_${id}_report.${format === 'excel' ? 'xlsx' : format}`
    link.click()
    URL.revokeObjectURL(url)
  },

  getAlerts: (includeResolved = false) =>
    fetchWithAuth<FleetAlert[]>(`/alerts/?include_resolved=${includeResolved}`),
  getAlertSummary: () => fetchWithAuth<AlertSummary>('/alerts/summary'),
  acknowledgeAlert: (id: number) =>
    fetchWithAuth<FleetAlert>(`/alerts/${id}/acknowledge`, { method: 'POST' }),

  getReleases: () => fetchWithAuth<AppRelease[]>('/releases/'),
  // sha256 is required, not nullable: the player refuses to install an APK it cannot
  // verify, so a release without one could never reach a screen.
  createRelease: (data: { version_code: number, version_name: string, apk_url: string, sha256: string, mandatory: boolean }) =>
    fetchWithAuth<AppRelease>('/releases/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),
  promoteRelease: (versionCode: number, rolloutState: RolloutState) =>
    fetchWithAuth<AppRelease>(`/releases/${versionCode}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ rollout_state: rolloutState }) }),
}
