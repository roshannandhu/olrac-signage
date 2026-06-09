import { client, unwrap } from './client'
import type { GroupDTO } from './types'
import type { PlaylistItemInput } from './playlists'

export const groupsApi = {
  list: () => unwrap<GroupDTO[]>(client.get('/groups')),

  create: (body: { name: string; screen_ids: string[] }) =>
    unwrap<GroupDTO>(client.post('/groups', body)),

  update: (id: string, body: { name?: string; screen_ids?: string[] }) =>
    unwrap<GroupDTO>(client.patch(`/groups/${id}`, body)),

  savePlaylist: (id: string, items: PlaylistItemInput[]) =>
    unwrap<unknown>(client.put(`/groups/${id}/playlist`, { items })),

  remove: (id: string) => unwrap<{ ok: boolean }>(client.delete(`/groups/${id}`)),
}
