import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { websitesApi, websiteToUi } from '../api'
import type { ApiError } from '../api'
import type { Website } from '../types'
import { useStore } from '../store'
import { qk } from './keys'

export function useWebsites() {
  return useQuery<Website[]>({
    queryKey: qk.websites,
    queryFn: () => websitesApi.list().then((rows) => rows.map(websiteToUi)),
  })
}

export function useAddWebsite() {
  const qc = useQueryClient()
  const pushToast = useStore((s) => s.pushToast)
  return useMutation({
    mutationFn: (body: { name: string; url: string }) => websitesApi.create(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.websites })
      pushToast('Website added!', 'success')
    },
    onError: (e: ApiError) => pushToast(e.message ?? 'Add failed', 'error'),
  })
}

export function useDeleteWebsite() {
  const qc = useQueryClient()
  const pushToast = useStore((s) => s.pushToast)
  return useMutation({
    mutationFn: (id: string) => websitesApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.websites })
      pushToast('Website removed', 'success')
    },
    onError: (e: ApiError) => pushToast(e.message ?? 'Remove failed', 'error'),
  })
}
