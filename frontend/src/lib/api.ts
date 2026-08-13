import { useAuthStore } from './store'
import type { AppRelease, BillingSummary, Campaign, CampaignExportFormat, CampaignInfo, CampaignPoint, CampaignStats, CheckoutSession, ContentItem, EmergencyBroadcast, EnrollmentToken, ItemSchedule, Plan, Playlist, Role, Screen, ScreenGroup, Screenshot, TransitionName, User } from './types'

const API_BASE = `${(process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '')}/api`

// The API lives on its own origin, so a WebSocket must be built from API_BASE and
// not from window.location — pointing it at the Next.js host silently never connects.
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
  getScreens: () => fetchWithAuth<Screen[]>('/screens/'),
  // Partial by design: sending only the edited keys stops a rename from resetting
  // orientation, which is not editable anywhere in the dashboard.
  patchScreen: (id: number, data: Partial<{
    name: string
    orientation: number
    group_id: number | null
    target_version_code: number | null
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

  getContent: () => fetchWithAuth<ContentItem[]>('/content/'),
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
  createUser: (data: { username: string; password: string; role: Role }) => fetchWithAuth<User>('/users/', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }),
  updateUser: (id: number, data: { role?: Role; is_active?: boolean }) => fetchWithAuth<User>(`/users/${id}`, {
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
    
  getScreenshots: (screenId: number) => fetchWithAuth<Screenshot[]>(`/screenshots?screen_id=${screenId}`),
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

  getReleases: () => fetchWithAuth<AppRelease[]>('/releases/'),
  createRelease: (data: { version_code: number, version_name: string, apk_url: string, sha256: string | null, mandatory: boolean }) =>
    fetchWithAuth<AppRelease>('/releases/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),
}
