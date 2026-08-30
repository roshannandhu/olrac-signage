'use client'

import { useMemo } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ArrowLeft, CheckCircle2, Film, MapPin, MonitorPlay, RefreshCw, TriangleAlert } from 'lucide-react'
import { EmptyState } from '@/components/dashboard/empty-state'
import { ErrorState } from '@/components/dashboard/error-state'
import { AdBookings } from '@/components/dashboard/ad-bookings'
import { MediaThumbnail } from '@/components/dashboard/media-thumbnail'
import { ScreenMap } from '@/components/dashboard/screen-map'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsIndicator, TabsList, TabsPanel, TabsTrigger } from '@/components/ui/tabs'
import { api } from '@/lib/api'
import { assetOrientation, clipDuration, formatBytes, relativeTime } from '@/lib/format'
import type { MediaPeriodStats, Playlist, Screen } from '@/lib/types'

function StatTile({ label, stats }: { label: string; stats: MediaPeriodStats }) {
  return (
    <div className="ring-hairline bg-card rounded-xl p-4 ring-1">
      <p className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">{label}</p>
      <p className="text-foreground mt-1.5 text-2xl font-bold tabular-nums">{stats.total_plays.toLocaleString()}</p>
      <p className="text-muted-foreground mt-0.5 text-xs">
        {stats.total_plays ? `${stats.success_percent}% completed` : 'No plays recorded'}
      </p>
    </div>
  )
}

export default function AdDetailPage() {
  const params = useParams()
  const contentId = Number(params.id)

  const contentQuery = useQuery({ queryKey: ['content'], queryFn: api.getContent })
  const groupsQuery = useQuery({ queryKey: ['groups'], queryFn: api.getGroups })
  const playlistsQuery = useQuery({ queryKey: ['playlists'], queryFn: api.getPlaylists })
  const screensQuery = useQuery({ queryKey: ['screens'], queryFn: api.getScreens })
  const reportQuery = useQuery({
    queryKey: ['media-report', contentId],
    queryFn: () => api.getMediaReport(contentId),
    enabled: Number.isFinite(contentId),
    refetchInterval: 10000,
  })

  const item = contentQuery.data?.find((entry) => entry.id === contentId)
  const groupName = (id: number | null | undefined) =>
    groupsQuery.data?.find((group) => group.id === id)?.name

  /**
   * Where this ad is scheduled right now, independent of play history.
   *
   * Proof-of-play only exists once a TV has actually played something, so a freshly
   * scheduled advert would otherwise look like it is running nowhere. This answers
   * "is it live?" from the assignment graph instead.
   */
  const scheduledOn = useMemo(() => {
    const playlists = (playlistsQuery.data || []) as Playlist[]
    const screens = (screensQuery.data || []) as Screen[]
    const playlistIds = new Set(
      playlists.filter((playlist) => (playlist.items || []).some((entry) => entry.content_id === contentId))
        .map((playlist) => playlist.id),
    )
    return screens.filter((screen) => screen.effective_playlist_id && playlistIds.has(screen.effective_playlist_id))
  }, [playlistsQuery.data, screensQuery.data, contentId])

  const placesScheduled = useMemo(
    () => new Set(scheduledOn.map((screen) => screen.group_id ?? `ungrouped-${screen.id}`)).size,
    [scheduledOn],
  )

  const backLink = (
    <Link href="/dashboard/content" className="text-muted-foreground hover:text-foreground mb-4 inline-flex items-center gap-2 text-sm font-medium">
      <ArrowLeft className="size-4" /> Back to content library
    </Link>
  )

  if (contentQuery.isError) {
    return <ErrorState message="This asset could not be loaded." onRetry={() => contentQuery.refetch()} />
  }
  if (contentQuery.isLoading) {
    return <div className="space-y-6"><Skeleton className="h-40" /><Skeleton className="h-64" /></div>
  }
  if (!item) {
    return (
      <div>
        {backLink}
        <EmptyState icon={Film} title="Asset not found" description="It may have been deleted from the library." action={<Button variant="outline" render={<Link href="/dashboard/content" />}>View library</Button>} />
      </div>
    )
  }

  const report = reportQuery.data
  const orientation = assetOrientation(item.renditions)
  const duration = clipDuration(item.duration_ms)
  const online = scheduledOn.filter((screen) => screen.status === 'online').length

  return (
    <div>
      {backLink}

      <header className="bg-secondary/50 ring-hairline mb-6 rounded-2xl p-4 ring-1 sm:p-5">
        <div className="flex flex-wrap items-start gap-5">
          <div className="bg-muted aspect-video w-56 shrink-0 overflow-hidden rounded-xl">
            <MediaThumbnail item={item} className="size-full" />
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="text-foreground text-2xl font-bold tracking-tight break-words">{item.name}</h1>
            <p className="text-muted-foreground mt-1 text-sm">
              <span className="capitalize">{item.type}</span>
              {orientation && ` • ${orientation}`}
              {duration && ` • ${duration}`}
              {` • added ${relativeTime(item.uploaded_at)}`}
            </p>

            <div className="mt-3 flex flex-wrap items-center gap-2">
              {item.status === 'ready' && <Badge variant="success"><CheckCircle2 className="size-3" /> Ready to play</Badge>}
              {item.status === 'processing' && <Badge variant="warning">Still processing</Badge>}
              {item.status === 'failed' && <Badge variant="danger"><TriangleAlert className="size-3" /> Processing failed</Badge>}
              {item.tags?.split(',').map((tag) => tag.trim()).filter(Boolean).map((tag) => (
                <Badge key={tag} variant="secondary">{tag}</Badge>
              ))}
            </div>

            {/* The headline answer to "is this ad working?" */}
            <p className="text-foreground mt-4 text-sm">
              {scheduledOn.length === 0 ? (
                <span className="text-muted-foreground">Not scheduled on any screen yet.</span>
              ) : (
                <>
                  Scheduled on <strong>{scheduledOn.length} screen{scheduledOn.length === 1 ? '' : 's'}</strong>
                  {' '}across <strong>{placesScheduled} group{placesScheduled === 1 ? '' : 's'}</strong>
                  {' — '}
                  <span className={online ? 'text-emerald-600 dark:text-emerald-400' : 'text-muted-foreground'}>
                    {online} online now
                  </span>
                </>
              )}
            </p>
          </div>
        </div>
      </header>

      {item.status === 'failed' && (
        <div className="border-destructive/30 bg-destructive/5 mb-6 rounded-xl border p-4">
          <p className="text-destructive text-sm font-semibold">This asset cannot play</p>
          <p className="text-muted-foreground mt-1 text-sm">{item.failed_reason || 'Processing did not complete.'}</p>
          <Button variant="outline" size="sm" className="mt-3" render={<Link href="/dashboard/content" />}>Retry from the library</Button>
        </div>
      )}

      <Tabs defaultValue="bookings">
        <TabsList>
          <TabsTrigger value="bookings">Bookings</TabsTrigger>
          <TabsTrigger value="playback">Playback</TabsTrigger>
          <TabsTrigger value="places">Groups &amp; screens</TabsTrigger>
          <TabsTrigger value="technical">Technical</TabsTrigger>
          <TabsIndicator />
        </TabsList>

        <TabsPanel value="bookings">
          <AdBookings contentId={contentId} />
        </TabsPanel>

        <TabsPanel value="playback">
          {reportQuery.isLoading ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">{Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-24 rounded-xl" />)}</div>
          ) : !report ? (
            <ErrorState message="The playback report could not be loaded." onRetry={() => reportQuery.refetch()} />
          ) : (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <p className="text-xs text-muted-foreground">Proof-of-play metrics auto-update in real-time as screens report in.</p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => reportQuery.refetch()}
                  disabled={reportQuery.isFetching}
                  className="bg-card gap-1.5 text-xs h-8"
                >
                  <RefreshCw className={`size-3.5 ${reportQuery.isFetching ? 'animate-spin' : ''}`} />
                  Refresh
                </Button>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <StatTile label="Today" stats={report.today} />
                <StatTile label="This week" stats={report.week} />
                <StatTile label="This month" stats={report.month} />
                <StatTile label="Lifetime" stats={report.lifetime} />
              </div>

              <Card className="ring-hairline bg-card border-0 ring-1">
                <CardContent className="p-5">
                  <h2 className="text-foreground mb-4 font-semibold">Plays over the last 30 days</h2>
                  {report.daily.length === 0 ? (
                    <p className="text-muted-foreground py-10 text-center text-sm">
                      No plays recorded yet. Figures appear once a screen reports playback.
                    </p>
                  ) : (
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={report.daily}>
                          <defs>
                            <linearGradient id="plays" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="var(--color-primary)" stopOpacity={0.35} />
                              <stop offset="100%" stopColor="var(--color-primary)" stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                          <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="var(--color-muted-foreground)" />
                          <YAxis allowDecimals={false} tick={{ fontSize: 12 }} stroke="var(--color-muted-foreground)" />
                          <Tooltip
                            contentStyle={{
                              background: 'var(--color-card)',
                              border: '1px solid var(--color-border)',
                              borderRadius: 12,
                              color: 'var(--color-foreground)',
                            }}
                          />
                          <Area type="monotone" dataKey="total_plays" name="Plays" stroke="var(--color-primary)" fill="url(#plays)" strokeWidth={2} />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          )}
        </TabsPanel>

        <TabsPanel value="places">
          <div className="space-y-6">
            <Card className="ring-hairline bg-card border-0 ring-1">
              <CardContent className="p-5">
                <h2 className="text-foreground mb-4 flex items-center gap-2 font-semibold">
                  <MapPin className="text-primary dark:text-brand size-4" /> Where this ad is on screen
                </h2>
                <ScreenMap points={scheduledOn.map((screen) => {
                  const played = report?.per_screen.find((row) => row.screen_id === screen.id)
                  return {
                    id: screen.id,
                    name: screen.name || `Screen ${screen.id}`,
                    location: screen.location,
                    latitude: screen.latitude,
                    longitude: screen.longitude,
                    online: screen.status === 'online',
                    detail: `${(played?.total_plays ?? 0).toLocaleString()} plays`,
                  }
                })} />
              </CardContent>
            </Card>

            <Card className="ring-hairline bg-card border-0 ring-1">
              <CardContent className="p-5">
                <h2 className="text-foreground mb-4 flex items-center gap-2 font-semibold">
                  <MapPin className="text-primary dark:text-brand size-4" /> Plays by location
                </h2>
                {!report?.per_location.length ? (
                  <p className="text-muted-foreground text-sm">
                    No plays reported yet. Put screens into groups so results roll up per venue.
                  </p>
                ) : (
                  <div className="divide-hairline divide-y">
                    {report.per_location.map((place) => (
                      <div key={place.location} className="flex items-center justify-between gap-4 py-3">
                        <div className="min-w-0">
                          <p className="text-foreground truncate text-sm font-medium">{place.location}</p>
                          <p className="text-muted-foreground text-xs">{place.screens} screen{place.screens === 1 ? '' : 's'}</p>
                        </div>
                        <span className="text-foreground shrink-0 font-mono text-sm tabular-nums">{place.total_plays.toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="ring-hairline bg-card border-0 ring-1">
              <CardContent className="p-5">
                <h2 className="text-foreground mb-4 flex items-center gap-2 font-semibold">
                  <MonitorPlay className="text-primary dark:text-brand size-4" /> Screens running this ad
                </h2>
                {scheduledOn.length === 0 ? (
                  <p className="text-muted-foreground text-sm">
                    Not scheduled anywhere. Add it to a playlist from a screen or group page.
                  </p>
                ) : (
                  <div className="divide-hairline divide-y">
                    {scheduledOn.map((screen) => {
                      const played = report?.per_screen.find((row) => row.screen_id === screen.id)
                      return (
                        <Link
                          key={screen.id}
                          href={`/dashboard/screens/${screen.id}`}
                          className="hover:bg-muted/50 -mx-2 flex items-center justify-between gap-4 rounded-lg px-2 py-3"
                        >
                          <div className="min-w-0">
                            <p className="text-foreground truncate text-sm font-medium">{screen.name || `Screen ${screen.id}`}</p>
                            <p className="text-muted-foreground text-xs">
                              {groupName(screen.group_id) || 'Not in a group'}
                              {played?.last_played && ` • last played ${relativeTime(played.last_played)}`}
                            </p>
                          </div>
                          <div className="flex shrink-0 items-center gap-3">
                            <span className="text-foreground font-mono text-sm tabular-nums">
                              {(played?.total_plays ?? 0).toLocaleString()}
                            </span>
                            <Badge variant={screen.status === 'online' ? 'success' : 'outline'}>
                              {screen.status === 'online' ? 'Online' : 'Offline'}
                            </Badge>
                          </div>
                        </Link>
                      )
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsPanel>

        <TabsPanel value="technical">
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card className="ring-hairline bg-card border-0 ring-1">
              <CardContent className="p-5">
                <h2 className="text-foreground mb-4 font-semibold">Source file</h2>
                <dl className="divide-hairline divide-y text-sm">
                  {[
                    ['Type', <span key="t" className="capitalize">{item.type}</span>],
                    ['Duration', duration || '—'],
                    ['Orientation', orientation || 'Unknown until transcoded'],
                    ['File size', formatBytes(item.file_size_bytes)],
                    ['Status', <span key="s" className="capitalize">{item.status}</span>],
                    ['Uploaded', relativeTime(item.uploaded_at)],
                  ].map(([label, value]) => (
                    <div key={String(label)} className="flex justify-between gap-4 py-2.5">
                      <dt className="text-muted-foreground">{label}</dt>
                      <dd className="text-foreground font-medium">{value}</dd>
                    </div>
                  ))}
                </dl>
              </CardContent>
            </Card>

            <Card className="ring-hairline bg-card border-0 ring-1">
              <CardContent className="p-5">
                <h2 className="text-foreground mb-4 font-semibold">Transcoded renditions</h2>
                {!item.renditions?.length ? (
                  <p className="text-muted-foreground text-sm">
                    {item.type === 'image'
                      ? 'Images are sent to screens as uploaded — no transcoding needed.'
                      : 'No renditions yet. They are produced when processing completes.'}
                  </p>
                ) : (
                  <div className="divide-hairline divide-y text-sm">
                    {[...item.renditions]
                      .sort((a, b) => b.width * b.height - a.width * a.height)
                      .map((rendition) => (
                        <div key={rendition.id} className="flex items-center justify-between gap-4 py-2.5">
                          <div className="min-w-0">
                            <p className="text-foreground font-medium">{rendition.resolution}</p>
                            <p className="text-muted-foreground text-xs">
                              {rendition.width}×{rendition.height}
                              {rendition.codec && ` • ${rendition.codec}`}
                            </p>
                          </div>
                          <span className="text-muted-foreground shrink-0 font-mono text-xs tabular-nums">
                            {formatBytes(rendition.file_size_bytes)}
                          </span>
                        </div>
                      ))}
                  </div>
                )}
                <p className="text-muted-foreground/70 mt-4 text-xs">
                  Each screen is sent the largest rendition its decoder, memory and panel can handle.
                </p>
              </CardContent>
            </Card>
          </div>
        </TabsPanel>
      </Tabs>
    </div>
  )
}
