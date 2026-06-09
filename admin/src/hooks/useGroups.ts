import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { groupsApi, groupToUi } from '../api'
import type { ApiError } from '../api'
import type { Group } from '../types'
import { useStore } from '../store'
import { qk } from './keys'

export function useGroups() {
  return useQuery<Group[]>({
    queryKey: qk.groups,
    queryFn: () => groupsApi.list().then((rows) => rows.map(groupToUi)),
  })
}

export function useCreateGroup() {
  const qc = useQueryClient()
  const pushToast = useStore((s) => s.pushToast)
  return useMutation({
    mutationFn: (body: { name: string; screen_ids: string[] }) => groupsApi.create(body),
    onSuccess: (g) => {
      qc.invalidateQueries({ queryKey: qk.groups })
      pushToast(`Group "${g.name}" created!`, 'success')
    },
    onError: (e: ApiError) => pushToast(e.message ?? 'Create failed', 'error'),
  })
}

export function useUpdateGroup() {
  const qc = useQueryClient()
  const pushToast = useStore((s) => s.pushToast)
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: { name?: string; screen_ids?: string[] } }) =>
      groupsApi.update(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.groups })
      pushToast('Group updated', 'success')
    },
    onError: (e: ApiError) => pushToast(e.message ?? 'Update failed', 'error'),
  })
}

export function useDeleteGroup() {
  const qc = useQueryClient()
  const pushToast = useStore((s) => s.pushToast)
  return useMutation({
    mutationFn: (id: string) => groupsApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.groups })
      pushToast('Group removed', 'success')
    },
    onError: (e: ApiError) => pushToast(e.message ?? 'Remove failed', 'error'),
  })
}
