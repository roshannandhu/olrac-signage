import { useAuthStore } from '../store'
import { presignR2Url } from '../r2-signer'

const PROD_API_URL = 'https://olrac-signage-32lh.onrender.com'
const configuredUrl = (process.env.NEXT_PUBLIC_API_URL || PROD_API_URL).replace(/\/$/, '')
export let API_BASE = `${configuredUrl}/api`
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
  if (urlStr.startsWith('s3://') || urlStr.startsWith('r2://') || urlStr.includes('/api/media/')) {
    const directR2 = presignR2Url(urlStr)
    if (directR2) return directR2
  }
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
    if (url.pathname.startsWith('/api/media/')) {
      const directR2 = presignR2Url(urlStr)
      if (directR2) return directR2
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
 */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

export async function authFetch(endpoint: string, options: RequestInit = {}): Promise<Response> {
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

export async function fetchWithAuth<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const response = await authFetch(endpoint, options)
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}
