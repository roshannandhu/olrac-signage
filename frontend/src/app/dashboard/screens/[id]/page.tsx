'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { EmptyState } from '@/components/dashboard/empty-state'
import { ErrorState } from '@/components/dashboard/error-state'
import { MediaThumbnail } from '@/components/dashboard/media-thumbnail'
import { PageHeader } from '@/components/dashboard/page-header'
import { StatusIndicator } from '@/components/dashboard/status-indicator'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { relativeTime } from '@/lib/format'
import type { Screen, Screenshot, ContentItem, MediaRendition } from '@/lib/types'
import { ArrowLeft, Camera, MonitorPlay, Settings, Tv2 } from 'lucide-react'

function selectRendition(content: ContentItem, screen: Screen): MediaRendition | null {
  if (!content.renditions || content.renditions.length === 0) return null
  
  if (!screen.screen_width) {
    return content.renditions.find(r => r.resolution === '720p') || null
  }
  
  let valid = [...content.renditions]
  
  if (screen.supported_video_codecs && screen.supported_video_codecs.length > 0) {
    const codecMap: Record<string, string[]> = {
      "h264": ["video/avc"],
      "hevc": ["video/hevc", "video/x-h265"],
      "vp8": ["video/x-vnd.on2.vp8"],
      "vp9": ["video/x-vnd.on2.vp9"],
      "av1": ["video/av01"]
    }
    valid = valid.filter(r => {
      if (!r.codec) return true
      const mimes = codecMap[r.codec.toLowerCase()] || [`video/${r.codec.toLowerCase()}`]
      return mimes.some(m => screen.supported_video_codecs!.includes(m))
    })
  }
  
  if (screen.max_decode_width && screen.max_decode_height) {
    valid = valid.filter(r => r.width <= screen.max_decode_width! && r.height <= screen.max_decode_height!)
  }
  
  if (screen.total_ram_mb && screen.total_ram_mb < 1536) {
    valid = valid.filter(r => Math.max(r.width, r.height) <= 1280)
  }
  
  if (screen.screen_width && screen.screen_height) {
    valid = valid.filter(r => r.width <= screen.screen_width! && r.height <= screen.screen_height!)
  }
  
  if (valid.length === 0) return null
  
  valid.sort((a, b) => (b.width * b.height) - (a.width * a.height))
  return valid[0]
}

export default function ScreenDetailPage() {
  const params = useParams()
  const queryClient = useQueryClient()
  const screenId = parseInt(params.id as string)

  const screensQuery = useQuery({
    queryKey: ['screens'],
    queryFn: api.getScreens,
  })
  
  const screen: Screen | undefined = screensQuery.data?.find((s) => s.id === screenId)

  const playlistQuery = useQuery({
    queryKey: ['playlist', screen?.effective_playlist_id],
    queryFn: () => api.getPlaylist(screen!.effective_playlist_id!),
    enabled: !!screen?.effective_playlist_id,
  })

  const screenshotsQuery = useQuery({
    queryKey: ['screenshots', screenId],
    queryFn: () => api.getScreenshots(screenId),
    refetchInterval: 5000,
  })

  const requestMutation = useMutation({
    mutationFn: () => api.requestScreenshot(screenId),
    onSuccess: () => {
      toast.success('Screenshot requested. It will appear here shortly.')
      queryClient.invalidateQueries({ queryKey: ['screenshots', screenId] })
    },
    onError: (err: Error) => {
      toast.error(err.message || 'Failed to request screenshot')
    },
  })

  const screenshots: Screenshot[] = screenshotsQuery.data || []
  const playlistItems = playlistQuery.data?.items || []

  const backLink = (
    <Link href="/dashboard/screens" className="text-muted-foreground hover:text-foreground inline-flex items-center gap-2 text-sm font-medium">
      <ArrowLeft className="size-4" /> Back to screens
    </Link>
  )

  if (screensQuery.isError) {
    return <ErrorState message="This screen could not be loaded." onRetry={() => screensQuery.refetch()} />
  }

  if (screensQuery.isLoading) {
    return <div className="space-y-8"><Skeleton className="h-24" /><div className="grid gap-6 lg:grid-cols-3"><Skeleton className="h-96" /><Skeleton className="h-96 lg:col-span-2" /></div></div>
  }

  if (!screen) {
    return (
      <div className="space-y-8">
        {backLink}
        <EmptyState icon={Tv2} title="Screen not found" description="It may have been removed from this workspace, or the link is out of date." action={<Button variant="outline" render={<Link href="/dashboard/screens" />}>View all screens</Button>} />
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {backLink}

      <PageHeader
        eyebrow="Screen detail"
        title={screen.name || `Screen ${screen.id}`}
        description="What this display reports about itself, the renditions it will receive, and recent proof of what is on the glass."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <StatusIndicator status={screen.status} />
            <Badge variant="outline">Seen {relativeTime(screen.last_seen)}</Badge>
          </div>
        }
      />

      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-1">
          {/* Hardware Capabilities */}
          <Card className="ring-hairline bg-card border-0 shadow-[0_1px_2px_rgba(15,23,42,.04)] ring-1">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Settings className="size-5" />
                Reported capabilities
              </CardTitle>
            </CardHeader>
            <CardContent>
              {screen.screen_width ? (
                <div className="space-y-4 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Resolution</span>
                    <span className="font-medium">{screen.screen_width}x{screen.screen_height} @ {screen.refresh_rate?.toFixed(0)}Hz</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">RAM</span>
                    <span className="font-medium">{screen.total_ram_mb} MB</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Storage</span>
                    <span className="font-medium">{screen.free_storage_mb} / {screen.total_storage_mb} MB</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Max Decode</span>
                    <span className="font-medium">{screen.max_decode_width}x{screen.max_decode_height}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Android OS</span>
                    <span className="font-medium">v{screen.android_version} (API {screen.sdk_int})</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Hardware</span>
                    <span className="font-medium">{screen.manufacturer} {screen.model}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Network</span>
                    <span className="font-medium capitalize">{screen.network_type}</span>
                  </div>
                  <div className="pt-2 border-t border-border">
                    <div className="text-muted-foreground mb-1">Codecs</div>
                    <div className="flex flex-wrap gap-1">
                      {screen.supported_video_codecs?.map((c, i) => (
                        <span key={i} className="px-2 py-0.5 rounded bg-muted text-xs font-mono">
                          {c.replace('video/', '')}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Capabilities have not been reported by this screen yet. It will receive a 720p fallback rendition.
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6 lg:col-span-2">
          {/* Active Playlist */}
          <Card className="ring-hairline bg-card border-0 shadow-[0_1px_2px_rgba(15,23,42,.04)] ring-1">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <MonitorPlay className="size-5" />
                Active playlist renditions
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!screen.effective_playlist_id ? (
                <p className="text-muted-foreground text-sm">No playlist assigned.</p>
              ) : playlistQuery.isLoading ? (
                <div className="space-y-3">{Array.from({ length: 3 }).map((_, index) => <Skeleton key={index} className="h-16" />)}</div>
              ) : playlistItems.length === 0 ? (
                <p className="text-muted-foreground text-sm">This playlist is empty.</p>
              ) : (
                <div className="space-y-3">
                  {playlistItems.map((item) => {
                    const rendition = selectRendition(item.content, screen)
                    return (
                      <div key={item.id} className="border-hairline flex items-center justify-between gap-3 rounded-xl border p-3">
                        <div className="flex min-w-0 items-center gap-3">
                          <MediaThumbnail item={item.content} className="h-10 w-16 shrink-0 rounded-lg" />
                          <div className="min-w-0">
                            <div className="truncate text-sm font-medium">{item.content.name}</div>
                            <div className="text-muted-foreground text-xs capitalize">{item.content.type}</div>
                          </div>
                        </div>
                        <div className="shrink-0 text-right">
                          <div className="text-sm font-medium">
                            {item.content.type === 'video' ? (rendition ? `${rendition.resolution} (${rendition.codec || 'unknown'})` : 'Original') : '—'}
                          </div>
                          <div className="text-muted-foreground text-xs">
                            {item.content.type === 'video' ? 'Selected rendition' : 'No rendition needed'}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Screenshots */}
          <Card className="ring-hairline bg-card border-0 shadow-[0_1px_2px_rgba(15,23,42,.04)] ring-1">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg">Screenshot gallery</CardTitle>
              <Button size="sm" variant="outline" onClick={() => requestMutation.mutate()} disabled={requestMutation.isPending}>
                <Camera data-icon="inline-start" /> {requestMutation.isPending ? 'Requesting…' : 'Request screenshot'}
              </Button>
            </CardHeader>
            <CardContent>
              {screenshotsQuery.isLoading ? (
                <div className="grid gap-4 sm:grid-cols-2">{Array.from({ length: 2 }).map((_, index) => <Skeleton key={index} className="aspect-video" />)}</div>
              ) : !screenshots.length ? (
                <EmptyState icon={Camera} title="No screenshots yet" description="Request one to confirm what this display is actually showing." />
              ) : (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  {screenshots.map((shot) => (
                    <figure key={shot.id} className="border-hairline bg-muted overflow-hidden rounded-xl border">
                      {/* eslint-disable-next-line @next/next/no-img-element -- player uploads are arbitrary remote URLs, not build-time assets */}
                      <img src={shot.url} alt={`Screen capture taken ${relativeTime(shot.created_at)}`} className="aspect-video h-auto w-full object-cover" />
                      <figcaption className="bg-card text-muted-foreground p-2 text-xs">{relativeTime(shot.created_at)}</figcaption>
                    </figure>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
