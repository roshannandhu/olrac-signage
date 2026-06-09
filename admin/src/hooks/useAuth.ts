import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { authApi } from '../api'
import type { ApiError } from '../api'
import { useStore } from '../store'
import { qk } from './keys'

export function useMe() {
  const authed = useStore((s) => s.authed)
  return useQuery({ queryKey: qk.me, queryFn: authApi.me, enabled: authed })
}

export function useLogin() {
  const qc = useQueryClient()
  const login = useStore((s) => s.login)
  const pushToast = useStore((s) => s.pushToast)
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) => authApi.login(email, password),
    onSuccess: () => {
      login()
      qc.invalidateQueries({ queryKey: qk.me })
      pushToast('Welcome back!', 'success')
    },
    onError: (e: ApiError) => pushToast(e.message ?? 'Login failed', 'error'),
  })
}

export function useLogout() {
  const qc = useQueryClient()
  const logout = useStore((s) => s.logout)
  return useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      logout()
      qc.clear()
    },
  })
}
