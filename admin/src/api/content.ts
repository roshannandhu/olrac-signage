import { client, unwrap } from './client'
import type { ContentDTO } from './types'

export interface ContentFilters {
  type?: 'video' | 'image'
  orientation?: 'landscape' | 'portrait'
  sort?: 'newest' | 'oldest' | 'az' | 'za'
  search?: string
  tags?: string // comma-separated
}

export const contentApi = {
  list: (filters: ContentFilters = {}) =>
    unwrap<ContentDTO[]>(client.get('/content', { params: filters })),

  upload: (file: File, name?: string, tags?: string) => {
    const form = new FormData()
    form.append('file', file)
    if (name) form.append('name', name)
    if (tags) form.append('tags', tags)
    return unwrap<ContentDTO>(client.post('/content/upload', form))
  },

  patch: (
    id: string,
    body: { name?: string; tags?: string; start_date?: string | null; expiry_date?: string | null },
  ) => unwrap<ContentDTO>(client.patch(`/content/${id}`, body)),

  remove: (id: string) => unwrap<{ ok: boolean }>(client.delete(`/content/${id}`)),
}
