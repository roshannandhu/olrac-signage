import { useAuthStore } from './store'
import type { Package, PackageWrite, TenantSummary, TenantScreen, TenantContent, TenantUser, AlertSummary, Branding, Client, TenantPlan, FleetAlert, BookingReport, Placement, MediaReport, FitMode, OperatingMode, RolloutState, SyncRole, AppRelease, BillingSummary, Campaign, CampaignExportFormat, CampaignInfo, CampaignPoint, CampaignStats, CheckoutSession, ContentItem, EmergencyBroadcast, EnrollmentToken, ItemSchedule, Plan, Playlist, Screen, TenantRole, ScreenGroup, Screenshot, TransitionName, User } from './types'

const PROD_API_URL = 'https://olrac-signage-32lh.onrender.com'
const configuredUrl = (process.env.NEXT_PUBLIC_API_URL || PROD_API_URL).replace(/\/$/, '')
let API_BASE = `${configuredUrl}/api`
export let API_HOST = configuredUrl

if (typeof window !== 'undefined') {
  try {
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    if (!isLocalhost && (API_BASE.includes('localhost') || API_BASE.includes('127.0.0.1'))) {
      API_BASE = `${PROD_API_URL}/api`
      API_HOST = PROD_API_URL
    } else if (isLocalhost && !process.env.NEXT_PUBLIC_API_URL) {
      API_BASE = 'http://localhost:8000/api'
      API_HOST = 'http://localhost:8000'
    }
  } catch {
    // Keep configured value
  }
}

export const WS_BASE = API_BASE.replace(/^http/, 'ws')

export function resolveMediaUrl(urlStr: string | null | undefined): string | undefined {
  if (!urlStr) return undefined
  if (urlStr.startsWith('/uploads/')) {
    return `${API_HOST}${urlStr}`
  }
  if (urlStr.startsWith('uploads/')) {
    return `${API_HOST}/${urlStr}`
  }
  try {
    const url = new URL(urlStr)
    if (url.pathname.startsWith('/uploads/')) {
      return `${API_HOST}${url.pathname}${url.search}`
    }
  } catch {}
  return urlStr
}


export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message)
  }
}

/**
 * Save a blob to the user's downloads.
 *
 * One implementation because the object URL has to be revoked afterwards, and a copy of
 * this that forgets to leaks the whole file for the life of the tab.
 */
function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
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
  authMethods: async () => {
    try {
      const response = await fetch(`${API_BASE}/auth/methods`)
      if (!response.ok) return { google: true, password: true }
      return (await response.json()) as { google: boolean; password: boolean }
    } catch {
      return { google: true, password: true }
    }
  },
  googleAuthUrl: async (redirectUri: string) => {
    const response = await fetch(`${API_BASE}/auth/google/url?redirect_uri=${encodeURIComponent(redirectUri)}`)
    if (!response.ok) return { url: null }
    return response.json() as Promise<{ url: string | null }>
  },

  loginWithGoogle: async (code: string, redirectUri: string) => {
    const response = await fetch(`${API_BASE}/auth/google`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, redirect_uri: redirectUri }),
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => null)
      throw new ApiError(detail?.detail || 'Google sign-in failed', response.status)
    }
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
      // Without this header fetch() labels a string body text/plain, FastAPI rejects it
      // before the handler ever runs, and the validation error it returns carries a list
      // in `detail` where authFetch expects a string -- so every link, however valid,
      // failed as "Something went wrong". The other 25 JSON calls here already set it.
      { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ link }) },
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
  // 204, so there is no body to read -- typed void rather than an object the caller would
  // find undefined at runtime. Archives the screen: play history keeps its attribution and
  // the panel is signed out of the workspace on its next contact.
  deleteScreen: (screenId: number) => fetchWithAuth<void>(`/screens/${screenId}`, { method: 'DELETE' }),
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

  // There used to be a `bookingReportPdfUrl` here, rendered straight into an <a href>.
  // That navigates without the Authorization header, so it 401'd every time -- the exact
  // trap the comment on downloadCampaignReport below already warned about. The report is
  // never stored anywhere: the endpoint builds the PDF per request and streams it, so the
  // only way to get at it is an authenticated fetch.
  fetchBookingReportPdf: async (placementId: number): Promise<{ blob: Blob; filename: string }> => {
    const response = await authFetch(`/placements/${placementId}/report.pdf`)
    if (!response.ok) throw new ApiError('The report could not be generated.', response.status)
    const disposition = response.headers.get('content-disposition') || ''
    const match = disposition.match(/filename="?([^"]+)"?/)
    return { blob: await response.blob(), filename: match?.[1] || `booking-${placementId}-report.pdf` }
  },

  downloadBookingReport: async (placementId: number) => {
    const { blob, filename } = await api.fetchBookingReportPdf(placementId)
    saveBlob(blob, filename)
  },

  /**
   * Hand the PDF to the device's share sheet, so a tenant can send it to their client from
   * WhatsApp, Gmail or anything else installed.
   *
   * Returns 'shared' | 'downloaded' so the caller can say which actually happened. Sharing
   * files is unsupported on desktop Firefox and parts of desktop Chrome, and Safari
   * additionally wants share() called inside the user gesture -- awaiting the fetch above
   * can cost that activation and throw NotAllowedError. Every one of those falls back to
   * saving the file rather than surfacing an error the operator can do nothing about.
   */
  shareBookingReport: async (placementId: number, title: string): Promise<'shared' | 'downloaded'> => {
    const { blob, filename } = await api.fetchBookingReportPdf(placementId)
    const file = new File([blob], filename, { type: 'application/pdf' })
    if (navigator.canShare?.({ files: [file] })) {
      try {
        await navigator.share({ files: [file], title })
        return 'shared'
      } catch (error) {
        // The user dismissing the sheet is not a failure, and must not then dump a file
        // into their downloads folder as a consolation prize.
        if ((error as Error)?.name === 'AbortError') return 'shared'
      }
    }
    saveBlob(blob, filename)
    return 'downloaded'
  },
  getPlacements: (contentId: number) => fetchWithAuth<Placement[]>(`/placements/?content_id=${contentId}`),
  createPlacement: (data: {
    content_id: number
    // One or the other: a client record is the supported path, a bare name still works.
    advertiser?: string
    client_id?: number | null
    // Naming a plan fills in price and, when ends_at is omitted, the end date from its
    // duration. Copied server side, so later repricing leaves this booking alone.
    plan_id?: number | null
    price_paise: number
    is_paid: boolean
    starts_at: string
    ends_at?: string
    notes?: string | null
    targets: { screen_id?: number; group_id?: number }[]
  }) => fetchWithAuth<Placement>('/placements/', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }),

  addPlacementExtension: (placementId: number, data: {
    extended_to: string; extended_from?: string
    additional_price_paise: number; is_paid: boolean; notes?: string | null
  }) => fetchWithAuth<Placement>(`/placements/${placementId}/extensions`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }),
  removePlacementExtension: (placementId: number, extensionId: number) =>
    fetchWithAuth<Placement>(`/placements/${placementId}/extensions/${extensionId}`, { method: 'DELETE' }),

  getBranding: () => fetchWithAuth<Branding>('/branding/'),
  updateBranding: (data: { brand_name?: string | null; brand_color?: string | null }) =>
    fetchWithAuth<Branding>('/branding/', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
    }),
  uploadBrandLogo: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    // No Content-Type header: the browser has to set the multipart boundary itself, and
    // naming it here produces a body FastAPI cannot parse.
    return fetchWithAuth<Branding>('/branding/logo', { method: 'POST', body: form })
  },
  removeBrandLogo: () => fetchWithAuth<Branding>('/branding/logo', { method: 'DELETE' }),

  getClients: () => fetchWithAuth<Client[]>('/clients/'),
  createClient: (data: { name: string; email?: string | null; phone?: string | null; notes?: string | null }) =>
    fetchWithAuth<Client>('/clients/', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
    }),
  updateClient: (id: number, data: Partial<{ name: string; email: string | null; phone: string | null; notes: string | null }>) =>
    fetchWithAuth<Client>(`/clients/${id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
    }),
  deleteClient: (id: number) => fetchWithAuth<{ status: string }>(`/clients/${id}`, { method: 'DELETE' }),

  getTenantPlans: (includeInactive = false) =>
    fetchWithAuth<TenantPlan[]>(`/tenant-plans/?include_inactive=${includeInactive}`),
  createTenantPlan: (data: {
    name: string; description?: string | null; duration_days: number
    max_locations: number; ad_slots: number; price_paise: number; support_tier: string
  }) => fetchWithAuth<TenantPlan>('/tenant-plans/', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }),
  updateTenantPlan: (id: number, data: Partial<{
    name: string; description: string | null; duration_days: number
    max_locations: number; ad_slots: number; price_paise: number; support_tier: string; is_active: boolean
  }>) => fetchWithAuth<TenantPlan>(`/tenant-plans/${id}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }),
  deleteTenantPlan: (id: number) =>
    fetchWithAuth<{ status: string; bookings?: number }>(`/tenant-plans/${id}`, { method: 'DELETE' }),

  updatePlacement: (id: number, data: Partial<{
    advertiser: string; price_paise: number; is_paid: boolean
    client_id: number | null; plan_id: number | null
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
  bringToFront: (screenId: number) => fetchWithAuth(`/screens/${screenId}/bring-to-front`, { method: 'POST' }),

  getCampaigns: () => fetchWithAuth<Campaign[]>('/analytics/campaigns'),
  getCampaign: (id: number) => fetchWithAuth<CampaignInfo>(`/analytics/campaigns/${id}`),
  getCampaignStats: (id: number) => fetchWithAuth<CampaignStats>(`/analytics/campaigns/${id}/stats`),
  getCampaignTimeseries: (id: number) => fetchWithAuth<CampaignPoint[]>(`/analytics/campaigns/${id}/timeseries`),
  // The export endpoint authenticates by header like every other route, so it cannot
  // be reached by navigating to a ?token= URL: that 401s and leaks the JWT into history.
  downloadCampaignReport: async (id: number, format: CampaignExportFormat) => {
    const response = await authFetch(`/analytics/campaigns/${id}/export?format=${format}`)
    const blob = await response.blob()
    saveBlob(blob, `campaign_${id}_report.${format === 'excel' ? 'xlsx' : format}`)
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

/**
 * Platform-operator calls. Separate object from `api` so it is obvious at the call site
 * that these are cross-tenant, and so a tenant page cannot reach for one by accident.
 *
 * Everything here goes through the same authFetch as the rest of the app, which matters
 * for two reasons the previous admin pages got wrong: they used bare fetch() with a
 * hand-built Authorization header, so an expired token showed an empty table instead of
 * redirecting to login; and they used RELATIVE `/api/...` URLs, which only resolve through
 * the dev-only rewrite in next.config.ts -- in production those requests hit the Vercel
 * origin and 404, so the whole approvals screen was dead once deployed.
 */
export const adminApi = {
  listTenants: (status?: string) =>
    fetchWithAuth<TenantSummary[]>(`/admin/tenants${status ? `?status=${encodeURIComponent(status)}` : ''}`),
  getTenant: (id: number) => fetchWithAuth<TenantSummary>(`/admin/tenants/${id}`),
  getTenantScreens: (id: number) => fetchWithAuth<TenantScreen[]>(`/admin/tenants/${id}/screens`),
  getTenantContent: (id: number) => fetchWithAuth<TenantContent[]>(`/admin/tenants/${id}/content`),
  getTenantUsers: (id: number) => fetchWithAuth<TenantUser[]>(`/admin/tenants/${id}/users`),

  approveTenant: (id: number, body: { plan_id?: number; max_screens?: number; max_ad_slots?: number }) =>
    fetchWithAuth<TenantSummary>(`/admin/tenants/${id}/approve`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    }),
  rejectTenant: (id: number, reason: string) =>
    fetchWithAuth<TenantSummary>(`/admin/tenants/${id}/reject`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reason }),
    }),
  suspendTenant: (id: number) =>
    fetchWithAuth<TenantSummary>(`/admin/tenants/${id}/suspend`, { method: 'POST' }),
  reinstateTenant: (id: number) =>
    fetchWithAuth<TenantSummary>(`/admin/tenants/${id}/reinstate`, { method: 'POST' }),
  updateQuota: (id: number, body: { plan_id?: number; max_screens?: number; max_ad_slots?: number }) =>
    fetchWithAuth<TenantSummary>(`/admin/tenants/${id}/quota`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    }),

  listPackages: () => fetchWithAuth<Package[]>('/admin/plans'),
  createPackage: (body: PackageWrite) =>
    fetchWithAuth<Package>('/admin/plans', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    }),
  updatePackage: (id: number, body: Partial<PackageWrite>) =>
    fetchWithAuth<Package>(`/admin/plans/${id}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    }),
  deletePackage: (id: number) =>
    fetchWithAuth<{ status: string; detail?: string }>(`/admin/plans/${id}`, { method: 'DELETE' }),

  getDemoVideo: () => fetchWithAuth<{ url: string; description?: string }>('/admin/demo-video'),
  setDemoVideo: (url: string, description?: string) =>
    fetchWithAuth<{ status: string; url: string }>('/admin/demo-video', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url, description }),
    }),
  uploadDemoVideo: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return fetchWithAuth<{ status: string; url: string; message: string }>('/admin/demo-video/upload', {
      method: 'POST', body: form,
    })
  },

  updateUserRole: (userId: number, role: 'super_admin' | 'owner' | 'editor' | 'viewer') =>
    fetchWithAuth<{ status: string; user_id: number; username: string; role: string; message: string }>(`/admin/users/${userId}/role`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role }),
    }),
}

