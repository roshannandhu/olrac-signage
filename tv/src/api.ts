export const API_URL = `http://${window.location.hostname}:8000`

export async function requestPairingCode() {
  const res = await fetch(`${API_URL}/screens/request-code`, { method: 'POST' })
  const json = await res.json()
  if (!res.ok) throw new Error(json.error?.message || 'Failed to request code')
  return json.data as { code: string; screen_token: string }
}

export async function fetchMe(token: string) {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/screens/me`, {
      headers: { Authorization: `Bearer ${token}` }
    })
  } catch (err: any) {
    err.isNetworkError = true;
    throw err;
  }
  
  const json = await res.json()
  if (!res.ok) {
    const err: any = new Error(json.error?.message || 'Failed to fetch me')
    err.status = res.status
    throw err
  }
  return json.data as { screen: any; playlist: any[] }
}
