import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { screensApi, screenToUi } from '../api'
import type { ApiError, OrientationEnum } from '../api'
import type { Screen } from '../types'
import { useStore } from '../store'
import { qk } from './keys'

export function useScreens() {
  return useQuery<Screen[]>({
    queryKey: qk.screens,
    queryFn: () => screensApi.list().then((rows) => rows.map(screenToUi)),
    refetchInterval: 30000, // keep the online/offline badge live
  })
}

export function usePairScreen() {
  const qc = useQueryClient()
  const pushToast = useStore((s) => s.pushToast)
  return useMutation({
    mutationFn: (body: { code: string; name: string; orientation: OrientationEnum }) => screensApi.pair(body),
    onSuccess: (s) => {
      qc.invalidateQueries({ queryKey: qk.screens })
      pushToast(`"${s.name}" paired!`, 'success')
    },
    onError: (e: ApiError) => pushToast(e.message ?? 'Pairing failed', 'error'),
  })
}

export function useUpdateScreen() {
  const qc = useQueryClient()
  const pushToast = useStore((s) => s.pushToast)
  return useMutation({
    mutationFn: ({
      id,
      body,
    }: {
      id: string
      body: { name?: string; description?: string; orientation?: OrientationEnum; tags?: string }
    }) => screensApi.update(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.screens })
      pushToast('Settings saved', 'success')
    },
    onError: (e: ApiError) => pushToast(e.message ?? 'Save failed', 'error'),
  })
}

export function useDeleteScreen() {
  const qc = useQueryClient()
  const pushToast = useStore((s) => s.pushToast)
  return useMutation({
    mutationFn: (id: string) => screensApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.screens })
      pushToast('Screen removed', 'success')
    },
    onError: (e: ApiError) => pushToast(e.message ?? 'Remove failed', 'error'),
  })
}
