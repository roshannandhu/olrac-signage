'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { ListVideo } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { api } from '@/lib/api'

export type AssignTarget =
  | { kind: 'screen'; id: number; name: string }
  | { kind: 'group'; id: number; name: string; screenCount: number }

/**
 * Shown wherever a screen or a group has nothing to play.
 *
 * Picking an existing loop and starting a new one are the only two things to do here, so
 * both are on screen at once rather than behind a choice.
 */
export function AssignPlaylistCard({ target }: { target: AssignTarget }) {
  const queryClient = useQueryClient()
  const [existingId, setExistingId] = useState<string | null>(null)
  const [newName, setNewName] = useState('')

  const playlistsQuery = useQuery({ queryKey: ['playlists'], queryFn: api.getPlaylists })
  const playlists = playlistsQuery.data || []

  const assign = (playlistId: number) =>
    target.kind === 'screen'
      ? api.assignPlaylist(target.id, playlistId)
      : api.assignGroupPlaylist(target.id, playlistId)

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['screens'] })
    queryClient.invalidateQueries({ queryKey: ['groups'] })
    queryClient.invalidateQueries({ queryKey: ['playlists'] })
  }

  const assignExisting = useMutation({
    mutationFn: (playlistId: number) => assign(playlistId),
    onSuccess: () => {
      refresh()
      toast.success(target.kind === 'screen'
        ? 'Playlist assigned. The screen picks it up on its next sync.'
        : 'Playlist assigned to every screen in this group.')
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const createAndAssign = useMutation({
    mutationFn: async () => {
      const playlist = await api.createPlaylist(newName.trim())
      await assign(playlist.id)
      return playlist
    },
    onSuccess: () => {
      refresh()
      toast.success('Playlist created and assigned.')
      setNewName('')
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const pending = assignExisting.isPending || createAndAssign.isPending

  return (
    <Card className="ring-hairline bg-card mx-auto max-w-xl border-0 ring-1">
      <CardContent className="space-y-6 p-6 text-center">
        <span className="bg-primary/10 text-primary dark:text-brand mx-auto grid size-12 place-items-center rounded-2xl">
          <ListVideo className="size-6" />
        </span>
        <div className="space-y-1">
          <h2 className="text-foreground font-semibold">
            {target.kind === 'screen' ? 'Nothing is scheduled on this screen' : 'This group has no playlist'}
          </h2>
          <p className="text-muted-foreground text-sm">
            {target.kind === 'screen'
              ? 'Give it a playlist and it will start looping on the next sync.'
              : `Assign one and all ${target.screenCount} screen${target.screenCount === 1 ? '' : 's'} will start looping it.`}
          </p>
        </div>

        {playlists.length > 0 && (
          <div className="flex gap-2">
            <Select value={existingId} onValueChange={(value) => setExistingId(value as string | null)}>
              <SelectTrigger className="w-full"><SelectValue placeholder="Use an existing playlist…" /></SelectTrigger>
              <SelectContent>
                {playlists.map((playlist) => (
                  <SelectItem key={playlist.id} value={String(playlist.id)}>{playlist.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button disabled={!existingId || pending} onClick={() => existingId && assignExisting.mutate(Number(existingId))}>
              Assign
            </Button>
          </div>
        )}

        <div className="flex gap-2">
          <Input
            value={newName}
            onChange={(event) => setNewName(event.target.value)}
            placeholder={`${target.name} loop`}
            aria-label="New playlist name"
          />
          <Button variant="outline" disabled={!newName.trim() || pending} onClick={() => createAndAssign.mutate()}>
            Create new
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
