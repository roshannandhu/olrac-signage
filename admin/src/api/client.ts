import axios, { type AxiosResponse } from 'axios'
import { supabase } from '../lib/supabase'
import { useStore } from '../store'

// Single axios instance for the Olrac FastAPI. baseURL from env (defaults to local).
export const client = axios.create({
  baseURL: `http://${window.location.hostname}:8000`,
})

// Attach the current Supabase access token to every request.
client.interceptors.request.use(async (config) => {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// On 401, drop the session and bounce to /login. Reject with the API's error
// object ({message, code}) so callers/hooks can show a useful toast.
client.interceptors.response.use(
  (resp) => resp,
  (error) => {
    const status = error?.response?.status
    if (status === 401) {
      void supabase.auth.signOut()
      useStore.getState().logout()
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    const apiError = error?.response?.data?.error
    return Promise.reject(apiError ?? { message: error?.message ?? 'Request failed', code: 'network_error' })
  },
)

// Every backend response is the envelope {data, error}. unwrap() returns the data.
export async function unwrap<T>(p: Promise<AxiosResponse<{ data: T; error: null }>>): Promise<T> {
  const r = await p
  return r.data.data
}

export interface ApiError {
  message: string
  code?: string
}
