import { client, unwrap } from './client'
import type { WebsiteDTO } from './types'

export const websitesApi = {
  list: () => unwrap<WebsiteDTO[]>(client.get('/websites')),

  create: (body: { name: string; url: string }) =>
    unwrap<WebsiteDTO>(client.post('/websites', body)),

  remove: (id: string) => unwrap<{ ok: boolean }>(client.delete(`/websites/${id}`)),
}
