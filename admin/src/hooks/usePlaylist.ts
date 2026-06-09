import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { playlistsApi } from '../api'
import type { ApiError, PlaylistItemDTO, PlaylistItemInput } from '../api'
import { useStore } from '../store'
import { qk } from './keys'

export function usePlaylist(screenId: string | undefined) {
  return useQuery<PlaylistItemDTO[]>({
    queryKey: qk.playlist(screenId ?? ''),
    queryFn: () => playlistsApi.get(screenId as string),
    enabled: !!screenId,
  })
}

export function useSavePlaylist() {
  const qc = useQueryClient()
  const pushToast = useStore((s) => s.pushToast)
  return useMutation({
    mutationFn: ({ screenId, items }: { screenId: string; items: PlaylistItemInput[] }) =>
      playlistsApi.save(screenId, items),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: qk.playlist(vars.screenId) })
      pushToast('Playlist saved!', 'success')
    },
    onError: (e: ApiError) => pushToast(e.message ?? 'Save failed', 'error'),
  })
}
