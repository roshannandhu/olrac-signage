import { createClient } from '@supabase/supabase-js'

// Supabase is used ONLY for admin auth (signInWithPassword / getSession / signOut).
// Every other piece of data goes through our FastAPI (see src/api/*). The access
// token from the Supabase session is attached to API requests by src/api/client.ts.
const url = import.meta.env.VITE_SUPABASE_URL as string | undefined
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined

if (!url || !anonKey) {
  // Don't throw — the app still runs on the mock layer until the backend env is set.
  console.warn(
    '[olrac] VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY are not set. ' +
      'Auth + live API calls will fail until you create admin/.env (see .env.example).',
  )
}

export const supabase = createClient(url ?? 'http://localhost:54321', anonKey ?? 'public-anon-key', {
  auth: { persistSession: true, autoRefreshToken: true },
})
