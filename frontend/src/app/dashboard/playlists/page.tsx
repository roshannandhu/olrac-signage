'use client'

import Link from 'next/link'
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, Clock3, ListPlus, ListVideo, Play, Plus } from 'lucide-react'
import { toast } from 'sonner'
import { EmptyState } from '@/components/dashboard/empty-state'
import { ErrorState } from '@/components/dashboard/error-state'
import { PageHeader } from '@/components/dashboard/page-header'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import { loopDuration, relativeTime } from '@/lib/format'
import { useAuthStore } from '@/lib/store'

export default function PlaylistsPage() {
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)
  const canEdit = user?.role === 'owner' || user?.role === 'editor'
  const playlistsQuery = useQuery({ queryKey: ['playlists'], queryFn: api.getPlaylists })
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const createMutation = useMutation({
    mutationFn: () => api.createPlaylist(name.trim()),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['playlists'] }); toast.success('Playlist created'); setOpen(false); setName('') },
    onError: (error: Error) => toast.error(error.message),
  })

  if (playlistsQuery.isError) return <ErrorState message="Playlists could not be loaded." onRetry={() => playlistsQuery.refetch()} />
  const playlists = playlistsQuery.data || []

  const createDialog = canEdit ? <Dialog open={open} onOpenChange={setOpen}>
    <DialogTrigger render={<Button />}><Plus data-icon="inline-start" /> New playlist</DialogTrigger>
    <DialogContent>
      <DialogHeader><DialogTitle>Create playlist</DialogTitle><DialogDescription>Start an ordered content loop, then add schedules in the builder.</DialogDescription></DialogHeader>
      <form onSubmit={(event) => { event.preventDefault(); createMutation.mutate() }} className="space-y-4 pt-2"><div className="space-y-2"><Label htmlFor="playlist-name">Playlist name</Label><Input id="playlist-name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Reception loop" autoFocus /></div><Button type="submit" className="w-full" disabled={!name.trim() || createMutation.isPending}>{createMutation.isPending ? 'Creating…' : 'Create playlist'}</Button></form>
    </DialogContent>
  </Dialog> : <Badge variant="outline">View only</Badge>

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Publishing" title="Playlists" description="Build ordered loops, schedule each asset precisely, and publish the result to a screen or an entire group." actions={createDialog} />

      {playlistsQuery.isLoading ? <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 6 }).map((_, index) => <Skeleton key={index} className="h-56" />)}</div> : !playlists.length ? (
        <EmptyState icon={ListPlus} title="No playlists yet" description="Create your first loop, then pull content from the media library into the timeline." action={canEdit ? <Button onClick={() => setOpen(true)}><Plus data-icon="inline-start" /> Create first playlist</Button> : undefined} />
      ) : (
        <div className="stagger grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {playlists.map((playlist, index) => {
            const duration = playlist.items.reduce((total, item) => total + item.duration, 0)
            const scheduled = playlist.items.filter((item) => item.start_at || item.end_at || item.schedule).length
            const colors = ['from-blue-700 to-sky-400', 'from-violet-600 to-fuchsia-400', 'from-amber-500 to-orange-400']
            return <Link href={`/dashboard/playlists/${playlist.id}`} key={playlist.id} style={{ '--i': index } as React.CSSProperties} className="group focus-visible:ring-primary rounded-2xl focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none">
              <Card className="h-full border-0 bg-card py-0 shadow-[0_1px_2px_rgba(15,23,42,.04)] ring-1 ring-hairline transition-all group-hover:-translate-y-0.5 group-hover:shadow-[0_18px_45px_rgba(15,23,42,.08)] motion-reduce:transform-none motion-reduce:transition-none">
                <div className="flex items-center justify-between p-5 pb-0"><span className={`grid size-11 place-items-center rounded-xl bg-gradient-to-br ${colors[index % colors.length]} text-white shadow-lg`}><ListVideo className="size-5" /></span><ArrowRight className="size-4 text-muted-foreground/40 transition-transform group-hover:translate-x-1 group-hover:text-foreground motion-reduce:transition-none" /></div>
                <CardContent className="p-5 pt-4"><h2 className="text-lg font-semibold tracking-[-0.02em] text-foreground">{playlist.name}</h2><p className="mt-1 text-xs text-muted-foreground/70">Updated {relativeTime(playlist.updated_at)}</p><div className="mt-6 grid grid-cols-3 divide-x divide-hairline rounded-xl bg-muted py-3 text-center"><div><p className="text-sm font-bold text-foreground">{playlist.items.length}</p><p className="mt-0.5 text-[10px] uppercase tracking-wide text-muted-foreground/70">Items</p></div><div><p className="text-sm font-bold text-foreground">{loopDuration(duration)}</p><p className="mt-0.5 text-[10px] uppercase tracking-wide text-muted-foreground/70">Loop</p></div><div><p className="text-sm font-bold text-foreground">{scheduled}</p><p className="mt-0.5 text-[10px] uppercase tracking-wide text-muted-foreground/70">Scheduled</p></div></div><div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground/70">{playlist.items.length ? <><Play className="size-3.5" /> Ready to publish</> : <><Clock3 className="size-3.5" /> Waiting for content</>}</div></CardContent>
              </Card>
            </Link>
          })}
        </div>
      )}
    </div>
  )
}
