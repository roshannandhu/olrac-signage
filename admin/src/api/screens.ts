import { client, unwrap } from './client'
import type { OrientationEnum, ScreenDTO } from './types'

export const screensApi = {
  list: () => unwrap<ScreenDTO[]>(client.get('/screens')),

  pair: (body: { code: string; name: string; orientation: OrientationEnum }) =>
    unwrap<ScreenDTO>(client.post('/screens/pair', body)),

  update: (
    id: string,
    body: { name?: string; description?: string; orientation?: OrientationEnum; tags?: string },
  ) => unwrap<ScreenDTO>(client.patch(`/screens/${id}`, body)),

  remove: (id: string) => unwrap<{ ok: boolean }>(client.delete(`/screens/${id}`)),
}
