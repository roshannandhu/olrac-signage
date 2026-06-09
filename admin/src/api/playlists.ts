import { client, unwrap } from './client'
import type { PlaylistItemDTO } from './types'

export interface PlaylistItemInput {
  content_id: string
  position: number
  duration_override?: number | null
}

export const playlistsApi = {
  get: (screenId: string) =>
    unwrap<PlaylistItemDTO[]>(client.get(`/screens/${screenId}/playlist`)),

  save: (screenId: string, items: PlaylistItemInput[]) =>
    unwrap<PlaylistItemDTO[]>(client.put(`/screens/${screenId}/playlist`, { items })),
}
