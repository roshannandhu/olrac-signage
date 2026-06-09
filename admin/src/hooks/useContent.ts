import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { contentApi, contentToMedia } from '../api'
import type { ApiError, ContentFilters } from '../api'
import type { Media } from '../types'
import { useStore } from '../store'
import { qk } from './keys'

export function useContent(filters: ContentFilters = {}) {
  return useQuery<Media[]>({
    queryKey: qk.content(filters),
    queryFn: () => contentApi.list(filters).then((rows) => rows.map(contentToMedia)),
  })
}

export function useUploadContent() {
  const qc = useQueryClient()
  const pushToast = useStore((s) => s.pushToast)
  return useMutation({
    mutationFn: ({ file, name, tags }: { file: File; name?: string; tags?: string }) =>
      contentApi.upload(file, name, tags),
    onSuccess: (c) => {
      qc.invalidateQueries({ queryKey: ['content'] })
      pushToast(`Uploaded ${c.name}`, 'success')
    },
    onError: (e: ApiError) => pushToast(e.message ?? 'Upload failed', 'error'),
  })
}

export function useDeleteContent() {
  const qc = useQueryClient()
  const pushToast = useStore((s) => s.pushToast)
  return useMutation({
    mutationFn: (id: string) => contentApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['content'] })
      pushToast('Content deleted', 'success')
    },
    onError: (e: ApiError) => pushToast(e.message ?? 'Delete failed', 'error'),
  })
}
