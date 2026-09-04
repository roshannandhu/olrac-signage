'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import {
  ArrowLeft,
  Building2,
  CalendarRange,
  CheckCircle2,
  Film,
  IndianRupee,
  Layers3,
  MapPin,
  MonitorPlay,
  Receipt,
  RefreshCw,
  TriangleAlert,
} from 'lucide-react'
import { EmptyState } from '@/components/dashboard/empty-state'
import { ErrorState } from '@/components/dashboard/error-state'
import { MediaThumbnail } from '@/components/dashboard/media-thumbnail'
import { EditClientAdModal } from '@/components/dashboard/edit-client-ad-modal'
import { ScreenMap } from '@/components/dashboard/screen-map'
import { AdBookings } from '@/components/dashboard/ad-bookings'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsIndicator, TabsList, TabsPanel, TabsTrigger } from '@/components/ui/tabs'
import { api } from '@/lib/api'
import {
  asDate,
  assetOrientation,
  bookingState,
  clipDuration,
  formatBytes,
  relativeTime,
  rupees,
} from '@/lib/format'
import { canEditTenantContent } from '@/lib/roles'
import { useAuthStore } from '@/lib/store'
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
  const [editModalOpen, setEditModalOpen] = useState(false)
  const user = useAuthStore((state) => state.user)
  const canEdit = canEditTenantContent(user)

  // One row, not the whole library. The page used to fetch every asset and pick this one
  // out in the browser, so anything past the listing's 500-row cap rendered "not found".
  const contentQuery = useQuery({
    queryKey: ['content', contentId],
    queryFn: () => api.getContentItem(contentId),
    enabled: Number.isFinite(contentId),
  })
  // The same key AdBookings uses, so mounting both costs one request. This is the
  // authoritative commercial record -- price, payment, per-location windows -- and the
  // header above the tabs is built from it rather than from the content row's summary.
  const placementsQuery = useQuery({
    queryKey: ['placements', contentId],
    queryFn: () => api.getPlacements(contentId),
    enabled: Number.isFinite(contentId),
  })
  const groupsQuery = useQuery({ queryKey: ['groups'], queryFn: api.getGroups })
  const playlistsQuery = useQuery({ queryKey: ['playlists'], queryFn: api.getPlaylists })
  const screensQuery = useQuery({ queryKey: ['screens'], queryFn: api.getScreens })
  const reportQuery = useQuery({
    queryKey: ['media-report', contentId],
    queryFn: () => api.getMediaReport(contentId),
    enabled: Number.isFinite(contentId),
    refetchInterval: 10000,
  })

  const item = contentQuery.data
  const groupName = (id: number | null | undefined) =>
    groupsQuery.data?.find((group) => group.id === id)?.name

  // Highest id, matching what serialize_content reports as the asset's current booking.
  const booking = useMemo(() => {
    const rows = placementsQuery.data || []
    return rows.length ? [...rows].sort((a, b) => b.id - a.id)[0] : null
  }, [placementsQuery.data])

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

  // The assignment graph is two queries deep; if either failed, scheduledOn is [] and
  // saying "not scheduled anywhere" would be stating a failure as a fact.
  const placementUnknown = playlistsQuery.isError || screensQuery.isError

  const backLink = (
    <Link href="/dashboard/content" className="text-muted-foreground hover:text-foreground mb-4 inline-flex items-center gap-2 text-sm font-medium">
      <ArrowLeft className="size-4" aria-hidden="true" /> Back to content library
    </Link>
  )

  if (contentQuery.isError) {
    return <ErrorState message="This asset could not be loaded." onRetry={() => contentQuery.refetch()} />
  }
  if (contentQuery.isLoading) {
    return (
      <div>
        <Skeleton className="mb-6 h-44 rounded-2xl" />
        <Skeleton className="mb-6 h-28 rounded-2xl" />
        <Skeleton className="h-96 rounded-2xl" />
      </div>
    )
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
  const state = booking ? bookingState(booking) : null

  const owed = booking
    ? (booking.total_price_paise ?? booking.price_paise) - (booking.payment?.amount_paise ?? 0)
    : 0

  // The four commercial facts. Every one of these used to be a tab click away, or absent
  // from the page entirely, on the screen where an operator answers "what did we sell?".
  const kpis = booking
    ? [
        {
          label: 'Booked window',
          icon: CalendarRange,
          value: booking.days_remaining != null ? `${Math.max(0, booking.days_remaining)}d left` : '—',
          note: `${asDate(booking.starts_at)} → ${asDate(booking.effective_ends_at || booking.ends_at)}${booking.extensions.length ? ' · extended' : ''}`,
        },
        {
          label: 'Contract value',
          icon: IndianRupee,
          value: rupees(booking.total_price_paise ?? booking.price_paise),
          note: booking.is_paid ? 'Paid in full' : owed > 0 ? `${rupees(owed)} owing` : 'Unpaid',
        },
        {
          label: 'On air',
          icon: MonitorPlay,
          value: String(booking.screens_used),
          note: booking.plan_max_locations > 0
            ? `of ${booking.plan_max_locations} on the ${booking.plan?.name || 'plan'}`
            : 'No location cap on this plan',
        },
        {
          label: 'Plays',
          icon: Film,
          value: (report?.lifetime.total_plays ?? 0).toLocaleString(),
          note: report?.lifetime.total_plays
            ? `${report.lifetime.success_percent}% completed`
            : 'No plays recorded yet',
        },
      ]
    : []

  return (
    <div>
      {backLink}

      {/* Hero: what the creative is, who bought it, and where it stands. Absorbs the
          separate "client overview" card that used to restate these badges below, with a
          second Edit button pointing at the same modal. */}
      <header className="bg-secondary/50 ring-hairline mb-6 rounded-2xl p-4 ring-1 sm:p-5">
        <div className="flex flex-wrap items-start gap-5">
          {/* Full width until sm, then a fixed thumbnail beside the text. Left at w-56 the
              224px thumbnail never wrapped on a phone, so the title column was squeezed to
              a strip and the edit button ran off the side. */}
          <div className="bg-muted aspect-video w-full shrink-0 overflow-hidden rounded-xl sm:w-56">
            <MediaThumbnail item={item} className="size-full" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <h1 className="text-foreground text-2xl font-bold tracking-tight break-words">{item.name}</h1>
                <p className="text-muted-foreground mt-1 text-sm">
                  <span className="capitalize">{item.type}</span>
                  {orientation && ` • ${orientation}`}
                  {duration && ` • ${duration}`}
                  {` • added ${relativeTime(item.uploaded_at)}`}
                </p>
              </div>
              {canEdit && (
                <Button variant="outline" size="sm" onClick={() => setEditModalOpen(true)}>
                  <Building2 data-icon="inline-start" /> Edit client &amp; ad details
                </Button>
              )}
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-2">
              <Badge variant="outline">
                <Building2 className="size-3" aria-hidden="true" /> {item.client_name || 'Direct advertiser'}
              </Badge>
              {item.plan_name && <Badge variant="secondary">{item.plan_name}</Badge>}
              {state && <Badge variant={state.tone}>{state.label}</Badge>}
              {item.status === 'ready' && <Badge variant="success"><CheckCircle2 className="size-3" aria-hidden="true" /> Ready to play</Badge>}
              {item.status === 'processing' && <Badge variant="warning">Still processing</Badge>}
              {item.status === 'failed' && <Badge variant="danger"><TriangleAlert className="size-3" aria-hidden="true" /> Processing failed</Badge>}
              {item.tags?.split(',').map((tag) => tag.trim()).filter(Boolean).map((tag) => (
                <Badge key={tag} variant="secondary">{tag}</Badge>
              ))}
            </div>

            {(item.client_email || item.client_phone) && (
              <p className="text-muted-foreground mt-2 truncate text-sm">
                {item.client_email}
                {item.client_email && item.client_phone && ' • '}
                {item.client_phone}
              </p>
            )}

            <p className="text-foreground mt-4 text-sm">
              {placementUnknown ? (
                <span className="text-muted-foreground">Could not check which screens this is on.</span>
              ) : scheduledOn.length === 0 ? (
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

      {booking ? (
        <section aria-label="Booking summary" className="stagger mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {kpis.map(({ label, value, icon: Icon, note }, index) => (
            <Card
              key={label}
              style={{ '--i': index } as React.CSSProperties}
              className="lift ring-hairline bg-card border-0 py-0 shadow-[0_1px_2px_rgba(15,23,42,.04)] ring-1"
            >
              <CardContent className="p-5">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-muted-foreground text-sm font-medium">{label}</p>
                  <span className="bg-primary/10 text-primary dark:text-brand grid size-9 shrink-0 place-items-center rounded-xl">
                    <Icon className="size-4" aria-hidden="true" />
                  </span>
                </div>
                <p className="text-foreground mt-5 text-3xl font-semibold tracking-[-0.04em] tabular-nums">{value}</p>
                <p className="text-muted-foreground/70 mt-1 text-xs">{note}</p>
              </CardContent>
            </Card>
          ))}
        </section>
      ) : placementsQuery.isError ? (
        <div className="mb-6">
          <ErrorState message="This advert's booking could not be loaded." onRetry={() => placementsQuery.refetch()} />
        </div>
      ) : !placementsQuery.isLoading ? (
        <div className="ring-hairline bg-card mb-6 flex flex-wrap items-center justify-between gap-3 rounded-2xl p-5 shadow-sm ring-1">
          <div className="flex items-center gap-2.5">
            <span className="bg-primary/10 text-primary dark:text-brand grid size-9 place-items-center rounded-xl">
              <Receipt className="size-4" aria-hidden="true" />
            </span>
            <div>
              <p className="text-foreground text-sm font-semibold">Not sold to anyone yet</p>
              <p className="text-muted-foreground text-xs">Record who is paying for this advert, for how long, and where it runs.</p>
            </div>
          </div>
        </div>
      ) : null}

      {item.status === 'failed' && (
        <div className="border-destructive/30 bg-destructive/5 mb-6 rounded-xl border p-4">
          <p className="text-destructive text-sm font-semibold">This asset cannot play</p>
          <p className="text-muted-foreground mt-1 text-sm">{item.failed_reason || 'Processing did not complete.'}</p>
          <Button variant="outline" size="sm" className="mt-3" render={<Link href="/dashboard/content" />}>Retry from the library</Button>
        </div>
      )}

      {/* Booking first: this is a sales product, and money is the first question. */}
      <Tabs defaultValue="booking">
        <TabsList>
          <TabsTrigger value="booking">Booking &amp; billing</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="places">Where it plays</TabsTrigger>
          <TabsTrigger value="technical">Technical</TabsTrigger>
          <TabsIndicator />
        </TabsList>

        <TabsPanel value="booking">
          <AdBookings contentId={contentId} />
        </TabsPanel>

        <TabsPanel value="performance">
          {reportQuery.isError ? (
            <ErrorState message="The playback report could not be loaded." onRetry={() => reportQuery.refetch()} />
          ) : reportQuery.isLoading ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">{Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-24 rounded-xl" />)}</div>
          ) : !report ? (
            <ErrorState message="The playback report could not be loaded." onRetry={() => reportQuery.refetch()} />
          ) : (
            <div className="space-y-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-muted-foreground text-xs">Proof-of-play metrics auto-update in real time as screens report in.</p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => reportQuery.refetch()}
                  disabled={reportQuery.isFetching}
                  className="bg-card h-8 text-xs"
                >
                  <RefreshCw data-icon="inline-start" className={reportQuery.isFetching ? 'animate-spin' : undefined} />
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
            {/* What each location was actually sold. The API has always returned a target's
                own window; nothing read it, so a booking sold as "airport 50 days, mall 30"
                was indistinguishable from a uniform one anywhere on this page. */}
            <Card className="ring-hairline bg-card border-0 ring-1">
              <CardContent className="p-5">
                <h2 className="text-foreground mb-4 flex items-center gap-2 font-semibold">
                  <CalendarRange className="text-primary dark:text-brand size-4" aria-hidden="true" /> Sold schedule per location
                </h2>
                {!booking?.targets.length ? (
                  <p className="text-muted-foreground text-sm">
                    This advert is not booked into any location yet.
                  </p>
                ) : (
                  <div className="divide-hairline divide-y">
                    {booking.targets.map((target) => (
                      <div key={target.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                        <div className="flex min-w-0 flex-1 items-center gap-2.5">
                          <span className="bg-primary/10 text-primary dark:text-brand grid size-8 shrink-0 place-items-center rounded-lg">
                            {target.kind === 'group'
                              ? <Layers3 className="size-4" aria-hidden="true" />
                              : <MonitorPlay className="size-4" aria-hidden="true" />}
                          </span>
                          <div className="min-w-0">
                            <p className="text-foreground truncate text-sm font-medium">{target.name}</p>
                            <p className="text-muted-foreground text-xs">
                              {target.starts_at && target.ends_at
                                ? `${asDate(target.starts_at)} → ${asDate(target.ends_at)}`
                                : 'Follows the booking window'}
                            </p>
                          </div>
                        </div>
                        <div className="flex shrink-0 items-center gap-2">
                          {target.days != null && <Badge variant="secondary">{target.days} days</Badge>}
                          {!target.is_placed && <Badge variant="warning">Removed by hand</Badge>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="ring-hairline bg-card border-0 ring-1">
              <CardContent className="p-5">
                <h2 className="text-foreground mb-4 flex items-center gap-2 font-semibold">
                  <MapPin className="text-primary dark:text-brand size-4" aria-hidden="true" /> Where this ad is on screen
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

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <Card className="ring-hairline bg-card border-0 ring-1">
                <CardContent className="p-5">
                  <h2 className="text-foreground mb-4 flex items-center gap-2 font-semibold">
                    <MapPin className="text-primary dark:text-brand size-4" aria-hidden="true" /> Plays by location
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
                    <MonitorPlay className="text-primary dark:text-brand size-4" aria-hidden="true" /> Screens running this ad
                  </h2>
                  {placementUnknown ? (
                    <ErrorState
                      message="The list of screens could not be loaded."
                      onRetry={() => { playlistsQuery.refetch(); screensQuery.refetch() }}
                    />
                  ) : scheduledOn.length === 0 ? (
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

      {canEdit && (
        <EditClientAdModal open={editModalOpen} onOpenChange={setEditModalOpen} contentItem={item} />
      )}
    </div>
  )
}
