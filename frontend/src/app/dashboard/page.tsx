'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { ArrowUpRight, Clock3, HardDrive, Image as ImageIcon, ListVideo, MonitorCheck, MonitorOff } from 'lucide-react'
import { PageHeader } from '@/components/dashboard/page-header'
import { ErrorState } from '@/components/dashboard/error-state'
import { StatusIndicator } from '@/components/dashboard/status-indicator'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import { loopDuration, relativeTime, storageUsedGb } from '@/lib/format'

export default function DashboardPage() {
  const screensQuery = useQuery({ queryKey: ['screens'], queryFn: api.getScreens, refetchInterval: 30_000 })
  const contentQuery = useQuery({ queryKey: ['content'], queryFn: api.getContent })
  const playlistsQuery = useQuery({ queryKey: ['playlists'], queryFn: api.getPlaylists })
  const groupsQuery = useQuery({ queryKey: ['groups'], queryFn: api.getGroups })
  const queries = [screensQuery, contentQuery, playlistsQuery, groupsQuery]

  if (queries.some((query) => query.isError)) {
    return <ErrorState message="The operations summary is temporarily unavailable." onRetry={() => queries.forEach((query) => query.refetch())} />
  }

  const screens = screensQuery.data || []
  const content = contentQuery.data || []
  const playlists = playlistsQuery.data || []
  const groups = groupsQuery.data || []
  const online = screens.filter((screen) => screen.status === 'online').length
  const offline = screens.filter((screen) => screen.status === 'offline').length
  const storage = screens.reduce((total, screen) => total + storageUsedGb(screen.storage_used), 0)
  const loading = queries.some((query) => query.isLoading)
  const recentPlaylists = [...playlists].sort((a, b) => +new Date(b.updated_at) - +new Date(a.updated_at)).slice(0, 4)
  // When the panel says screens are offline it has to show those screens: listing the
  // first three in id order meant the headline and the tiles below it disagreed.
  const spotlight = (offline ? screens.filter((screen) => screen.status !== 'online') : screens).slice(0, 3)

  const stats = [
    { label: 'Screens online', value: `${online}/${screens.length}`, icon: MonitorCheck, tint: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400', note: offline ? `${offline} need attention` : 'All reporting normally' },
    { label: 'Media assets', value: content.length, icon: ImageIcon, tint: 'bg-violet-500/10 text-violet-600 dark:text-violet-400', note: `${content.filter((item) => item.type === 'video').length} videos in library` },
    { label: 'Active playlists', value: playlists.length, icon: ListVideo, tint: 'bg-amber-500/10 text-amber-600 dark:text-amber-400', note: `${groups.length} screen groups` },
    { label: 'Device storage', value: `${storage.toFixed(1)} GB`, icon: HardDrive, tint: 'bg-sky-500/10 text-sky-600 dark:text-sky-400', note: 'Reported usage across players' },
  ]

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Network pulse" title="Good to see you." description="A live view of your signage network, recent publishing activity, and anything that needs a closer look." />

      <section aria-label="Network statistics" className="stagger grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {loading ? Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-36" />) : stats.map(({ label, value, icon: Icon, tint, note }, index) => (
          <Card key={label} style={{ '--i': index } as React.CSSProperties} className="lift ring-hairline bg-card border-0 py-0 shadow-[0_1px_2px_rgba(15,23,42,.04),0_8px_30px_rgba(15,23,42,.04)] ring-1 hover:shadow-[0_1px_2px_rgba(15,23,42,.04),0_14px_40px_rgba(15,23,42,.08)]">
            <CardContent className="p-5">
              <div className="flex items-start justify-between">
                <p className="text-muted-foreground text-sm font-medium">{label}</p>
                <span className={`grid size-9 place-items-center rounded-xl ${tint}`}><Icon className="size-4" aria-hidden="true" /></span>
              </div>
              <p className="text-foreground mt-5 text-3xl font-semibold tabular-nums tracking-[-0.04em]">{value}</p>
              <p className="text-muted-foreground/70 mt-1 text-xs">{note}</p>
            </CardContent>
          </Card>
        ))}
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.35fr_.65fr]">
        <section className="bg-panel overflow-hidden rounded-2xl text-white shadow-[0_18px_50px_rgba(7,26,29,.16)]">
          <div className="signal-grid flex min-h-[250px] flex-col justify-between p-6 sm:p-8">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand">Network health</p>
                <h2 className="mt-3 text-2xl font-semibold tracking-[-0.03em]">{offline ? `${offline} screen${offline === 1 ? '' : 's'} offline` : 'All systems are on air'}</h2>
                <p className="mt-2 max-w-lg text-sm leading-6 text-white/50">{offline ? 'Review the devices below to check power, network access, or the player heartbeat.' : 'Every paired display is reporting successfully. Scheduled content will continue from local cache if a connection drops.'}</p>
              </div>
              <Badge className={offline ? 'border-amber-300/20 bg-amber-300/10 text-amber-200' : 'border-brand/25 bg-brand/10 text-brand'}>
                <span className={`size-1.5 rounded-full ${offline ? 'bg-amber-300' : 'bg-brand'}`} /> {offline ? 'Attention' : 'Healthy'}
              </Badge>
            </div>
            <div className="mt-8 grid gap-3 sm:grid-cols-3">
              {spotlight.map((screen) => (
                <div key={screen.id} className="rounded-xl border border-white/10 bg-white/[.055] p-4 backdrop-blur-sm">
                  <div className="flex items-center justify-between gap-3"><p className="truncate text-sm font-medium">{screen.name || `Screen ${screen.id}`}</p><StatusIndicator status={screen.status} /></div>
                  <p className="mt-3 text-xs text-white/35">Seen {relativeTime(screen.last_seen)}</p>
                </div>
              ))}
              {!screens.length && <p className="col-span-3 rounded-xl border border-dashed border-white/15 p-5 text-sm text-white/45">Pair your first screen to start monitoring the network.</p>}
            </div>
          </div>
        </section>

        <section className="bg-card ring-hairline rounded-2xl p-6 shadow-[0_1px_2px_rgba(15,23,42,.04)] ring-1">
          <div className="flex items-center justify-between">
            <div><p className="text-muted-foreground/70 text-xs font-bold tracking-[0.16em] uppercase">Publishing</p><h2 className="text-foreground mt-1 text-lg font-semibold">Recently updated</h2></div>
            <Link href="/dashboard/playlists" className="text-muted-foreground hover:bg-accent hover:text-accent-foreground grid size-9 place-items-center rounded-lg transition-colors" aria-label="View all playlists"><ArrowUpRight className="size-4" /></Link>
          </div>
          <div className="divide-hairline mt-5 divide-y">
            {recentPlaylists.map((playlist) => (
              <Link key={playlist.id} href={`/dashboard/playlists/${playlist.id}`} className="hover:bg-accent/40 -mx-2 flex items-center gap-3 rounded-lg px-2 py-3.5 transition-colors">
                <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400"><ListVideo className="size-4" /></span>
                <div className="min-w-0 flex-1"><p className="text-foreground truncate text-sm font-medium">{playlist.name}</p><p className="text-muted-foreground/70 mt-0.5 text-xs">{playlist.items.length} items · {loopDuration(playlist.items.reduce((sum, item) => sum + item.duration, 0))}</p></div>
                <span className="text-muted-foreground/70 text-xs">{relativeTime(playlist.updated_at)}</span>
              </Link>
            ))}
            {!recentPlaylists.length && <div className="py-8 text-center"><Clock3 className="text-muted-foreground/40 mx-auto size-5" /><p className="text-muted-foreground mt-2 text-sm">No playlists yet</p></div>}
          </div>
        </section>
      </div>

      {offline > 0 && (
        <section className="rounded-2xl border border-amber-500/25 bg-amber-500/10 p-5 sm:flex sm:items-center sm:justify-between">
          <div className="flex items-start gap-3"><MonitorOff className="mt-0.5 size-5 text-amber-600 dark:text-amber-400" /><div><p className="font-semibold text-amber-950 dark:text-amber-100">Offline screens detected</p><p className="mt-1 text-sm text-amber-700 dark:text-amber-300/80">Cached media keeps playing, but content changes will wait for those devices to reconnect.</p></div></div>
          <Link href="/dashboard/screens" className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-amber-900 hover:underline sm:mt-0 dark:text-amber-200">Review screens <ArrowUpRight className="size-4" /></Link>
        </section>
      )}
    </div>
  )
}
