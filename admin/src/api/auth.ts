import { client, unwrap } from './client'
import { supabase } from '../lib/supabase'
import type { ProfileDTO } from './types'

export const authApi = {
  // Admin sign-in goes through Supabase Auth (it sets the session whose access
  // token the axios interceptor then attaches to every API call).
  login: async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) throw { message: error.message, code: 'bad_credentials' }
    return data.session
  },

  logout: async () => {
    await supabase.auth.signOut()
  },

  // Current admin profile from our backend (verifies the Supabase token).
  me: () => unwrap<ProfileDTO>(client.get('/auth/me')),
}
