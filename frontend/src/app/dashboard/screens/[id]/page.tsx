'use client'

import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft, Clock, Info, Loader2, Monitor, MonitorPlay, PlaySquare, Settings, Smartphone, Trash2, Tv2 } from 'lucide-react'
import { EmptyState } from '@/components/dashboard/empty-state'
import { ErrorState } from '@/components/dashboard/error-state'
import { OverlayBadge } from '@/components/dashboard/asset-card'
import { PlaylistBuilder } from '@/components/dashboard/playlist-builder'
import { ScreenDetailsDrawer } from '@/components/dashboard/screen-details-drawer'
import { ScreenHoursDialog } from '@/components/dashboard/screen-hours-dialog'
import { KioskExitCard } from '@/components/dashboard/kiosk-exit-card'
import { ScreenMap } from '@/components/dashboard/screen-map'
import { ScreenSettingsDialog } from '@/components/dashboard/screen-settings-dialog'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import { relativeTime } from '@/lib/format'
import { canEditTenantContent } from '@/lib/roles'
import { useAuthStore } from '@/lib/store'
import type { Screen } from '@/lib/types'

const orientationLabel = (degrees: number) =>
  degrees === 90 || degrees === 270 ? 'Portrait orientation' : 'Landscape orientation'

/**
 * Always renders the PlaylistBuilder for a screen. If the screen has no playlist yet
 * (pre-migration data), it calls ensure-playlist to provision one on the fly, then
 * refreshes the screens query so the page re-renders with a valid playlist id.
 */
function ScreenPlaylistSection({ screen, screenId, inherited }: { screen: Screen; screenId: number; inherited: boolean }) {
  const queryClient = useQueryClient()

  const ensureMutation = useMutation({
    mutationFn: () => api.ensureScreenPlaylist(screenId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['screens'] }),
    onError: (error: Error) => toast.error(`Could not provision playlist: ${error.message}`),
  })

  useEffect(() => {
    if (!screen.effective_playlist_id && !ensureMutation.isPending && !ensureMutation.isSuccess) {
      ensureMutation.mutate()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [screen.effective_playlist_id])

  if (!screen.effective_playlist_id) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
        <Loader2 className="size-8 animate-spin mb-3" />
        <p className="text-sm font-medium">Setting up playlist…</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {inherited && (
        <div className="border-hairline bg-secondary/50 text-muted-foreground rounded-xl border p-3.5 text-sm">
          This loop comes from the screen&apos;s group, so changes here apply to{' '}
          <strong className="text-foreground font-medium">every screen in that group</strong>.{' '}
          <Link href="/dashboard/groups" className="text-primary dark:text-brand underline underline-offset-2">Manage groups</Link>
        </div>
      )}
      <PlaylistBuilder playlistId={screen.effective_playlist_id} showHeader={false} />
    </div>
  )
}

export default function ScreenDetailPage() {
  const params = useParams()
  const router = useRouter()
  const screenId = Number(params.id)
  const user = useAuthStore((state) => state.user)
  const canEdit = canEditTenantContent(user)

  const screensQuery = useQuery({ queryKey: ['screens'], queryFn: api.getScreens })
  const screens = useMemo(() => screensQuery.data || [], [screensQuery.data])
  const screen: Screen | undefined = screens.find((s) => s.id === screenId)

  const [settingsOpen, setSettingsOpen] = useState(false)
  const [hoursOpen, setHoursOpen] = useState(false)
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)

  const bringToFrontMutation = useMutation({
    mutationFn: () => api.bringToFront(screenId),
    onSuccess: () => toast.success('Command sent: opening signage app on screen.'),
    onError: (error: Error) => toast.error(error.message),
  })

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteScreen(screenId),
    onSuccess: () => {
      toast.success('Display removed and unpairing signal sent')
      router.push('/dashboard/screens')
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const backLink = (
    <Link href="/dashboard/screens" className="text-muted-foreground hover:text-foreground mb-4 inline-flex items-center gap-2 text-sm font-medium">
      <ArrowLeft className="size-4" /> Back to screens
    </Link>
  )

  if (screensQuery.isError) {
    return <ErrorState message="This screen could not be loaded." onRetry={() => screensQuery.refetch()} />
  }

  if (screensQuery.isLoading) {
    return <div className="space-y-6"><Skeleton className="h-32" /><Skeleton className="h-[480px]" /></div>
  }

  if (!screen) {
    return (
      <div>
        {backLink}
        <EmptyState icon={Tv2} title="Screen not found" description="It may have been removed from this workspace, or the link is out of date." action={<Button variant="outline" render={<Link href="/dashboard/screens" />}>View all screens</Button>} />
      </div>
    )
  }

  const label = screen.name || `Screen ${screen.id}`
  const online = screen.status === 'online'
  // A screen with no playlist of its own can still be playing one inherited from its
  // group; editing that loop changes every screen in the group, so it is called out.
  const inherited = !screen.playlist_id && Boolean(screen.effective_playlist_id)

  return (
    <div>
      {backLink}

      <header className="bg-secondary/50 ring-hairline mb-6 rounded-2xl p-4 ring-1 sm:p-5">
        <div className="flex flex-wrap items-start gap-4">
          <div className="bg-muted relative aspect-video w-40 shrink-0 overflow-hidden rounded-xl sm:w-48">
            {screen.latest_screenshot ? (
              // eslint-disable-next-line @next/next/no-img-element -- player uploads are arbitrary remote URLs, not build-time assets
              <img src={screen.latest_screenshot} alt={`What ${label} is showing`} className="size-full object-cover" />
            ) : (
              <div className="text-muted-foreground/40 grid size-full place-items-center"><MonitorPlay className="size-8" aria-hidden="true" /></div>
            )}
            <div className="absolute bottom-2 left-2">
              <OverlayBadge tone={online ? 'online' : 'offline'}>{online ? 'Online' : 'Offline'}</OverlayBadge>
            </div>
          </div>

          <div className="min-w-0 flex-1">
            <h1 className="text-foreground truncate text-2xl font-bold tracking-tight">{label}</h1>
            {screen.description && <p className="text-muted-foreground mt-0.5 text-sm">{screen.description}</p>}
            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
              <span className="text-muted-foreground text-sm">
                {online ? 'Online now' : `Last seen ${relativeTime(screen.last_seen)}`}
              </span>
              <button
                onClick={() => setDetailsOpen(true)}
                className="text-primary dark:text-brand hover:bg-accent flex cursor-pointer items-center gap-1.5 rounded-lg px-2 py-1 text-sm font-medium"
              >
                <Info className="size-4" aria-hidden="true" /> Details
              </button>
              {canEdit && (
                <button
                  onClick={() => bringToFrontMutation.mutate()}
                  disabled={bringToFrontMutation.isPending}
                  className="text-primary dark:text-brand hover:bg-accent flex cursor-pointer items-center gap-1.5 rounded-lg px-2 py-1 text-sm font-medium"
                >
                  <PlaySquare className="size-4" aria-hidden="true" /> {bringToFrontMutation.isPending ? 'Opening…' : 'Open app on TV'}
                </button>
              )}
            </div>
          </div>

          <div className="flex flex-col items-start gap-2 sm:items-end">
            <span className="text-muted-foreground flex items-center gap-2 text-sm">
              {screen.orientation === 90 || screen.orientation === 270
                ? <Smartphone className="size-4" aria-hidden="true" />
                : <Monitor className="size-4" aria-hidden="true" />}
              {orientationLabel(screen.orientation ?? 0)}
            </span>
            {canEdit && (
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setSettingsOpen(true)}
                  className="text-primary dark:text-brand hover:bg-accent flex cursor-pointer items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium"
                >
                  <Settings className="size-4" aria-hidden="true" /> Settings
                </button>
                <button
                  onClick={() => setHoursOpen(true)}
                  className="text-primary dark:text-brand hover:bg-accent flex cursor-pointer items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium"
                >
                  <Clock className="size-4" aria-hidden="true" /> Hours
                </button>
                <button
                  onClick={() => setDeleteOpen(true)}
                  className="text-destructive hover:bg-destructive/10 flex cursor-pointer items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium"
                >
                  <Trash2 className="size-4" aria-hidden="true" /> Remove
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Before the map and the timeline: somebody opening this page because they are standing
          in front of a screen they cannot get into needs it first, not last. */}
      <div className="mb-6">
        <KioskExitCard screen={screen} />
      </div>

      {screen.location && (
        <div className="mb-6">
          <ScreenMap
            points={[{
              id: screen.id,
              name: label,
              location: screen.location,
              latitude: screen.latitude,
              longitude: screen.longitude,
              online: online,
            }]}
            height={220}
          />
        </div>
      )}

      {/* No commercial list here. This page is about what the screen PLAYS -- the loop
          below, and the content library it is built from. The bookings sold onto it are a
          commercial record that belongs to the advert, and repeating it here made the page
          two things at once. It lives on the ad detail page, which is where it can be
          edited rather than only stared at. */}

      {/* Every screen gets its own playlist at pairing time. If one is still missing
          (pre-migration data), the ensure-playlist call provisions it on the fly. */}
      <ScreenPlaylistSection screen={screen} screenId={screenId} inherited={inherited} />

      {canEdit && (
        <>
          <ScreenSettingsDialog
            // Remount on close so the form re-reads the saved screen rather than keeping
            // whatever was half-typed last time.
            key={`settings-${settingsOpen}`}
            screen={screen}
            siblings={screens.filter((candidate) => candidate.id !== screen.id)}
            open={settingsOpen}
            onOpenChange={setSettingsOpen}
          />
          <ScreenHoursDialog key={`hours-${hoursOpen}`} screen={screen} open={hoursOpen} onOpenChange={setHoursOpen} />
          <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle>Remove {label}?</DialogTitle>
                {/* Says what is actually cleared and what is not. "Permanently" was not
                    true: the screen is archived precisely so its play history survives, and
                    that history is what client reports and past invoices are built from. */}
                <DialogDescription>
                  The TV is signed out immediately, clears its content and returns to the
                  pairing screen. Its slot is freed, so you can pair another display in its
                  place. Play history is kept, so past campaign reports and invoices stay
                  correct — and the same TV can be paired again later.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter className="gap-2 sm:gap-0">
                <Button variant="outline" onClick={() => setDeleteOpen(false)}>Cancel</Button>
                <Button
                  variant="destructive"
                  disabled={deleteMutation.isPending}
                  onClick={() => deleteMutation.mutate()}
                >
                  {deleteMutation.isPending ? 'Removing…' : 'Remove Display'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </>
      )}
      <ScreenDetailsDrawer screen={screen} open={detailsOpen} onOpenChange={setDetailsOpen} />
    </div>
  )
}
