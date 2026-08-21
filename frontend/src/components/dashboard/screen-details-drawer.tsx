'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Camera, X } from 'lucide-react'
import { Dialog as BaseDialog } from '@base-ui/react/dialog'
import { EmptyState } from '@/components/dashboard/empty-state'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsIndicator, TabsList, TabsPanel, TabsTrigger } from '@/components/ui/tabs'
import { api } from '@/lib/api'
import { relativeTime } from '@/lib/format'
import type { Screen, Screenshot } from '@/lib/types'

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="border-hairline flex items-center justify-between gap-4 border-b py-3.5 text-sm last:border-0">
      <span className="text-muted-foreground shrink-0">{label}</span>
      <span className="text-foreground text-right font-medium">{value ?? '—'}</span>
    </div>
  )
}

const dateTime = (value: string | null | undefined) =>
  value ? new Date(value).toLocaleString() : '—'

/**
 * Everything the device reports about itself, in a drawer rather than a tab.
 *
 * It is reference material an operator checks when something looks wrong, so it should
 * not cost them the playlist they were editing.
 */
export function ScreenDetailsDrawer({
  screen,
  open,
  onOpenChange,
}: {
  screen: Screen
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const queryClient = useQueryClient()

  const screenshotsQuery = useQuery({
    queryKey: ['screenshots', screen.id],
    queryFn: () => api.getScreenshots(screen.id),
    enabled: open,
    refetchInterval: open ? 5000 : false,
  })
  const screenshots: Screenshot[] = screenshotsQuery.data || []

  const requestShot = useMutation({
    mutationFn: () => api.requestScreenshot(screen.id),
    onSuccess: () => {
      toast.success('Screenshot requested. It will appear here shortly.')
      queryClient.invalidateQueries({ queryKey: ['screenshots', screen.id] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  return (
    <BaseDialog.Root open={open} onOpenChange={onOpenChange}>
      <BaseDialog.Portal>
        <BaseDialog.Backdrop className="fixed inset-0 z-50 bg-black/30 backdrop-blur-[2px]" />
        <BaseDialog.Popup className="bg-card fixed inset-y-0 right-0 z-50 flex w-full max-w-lg flex-col shadow-2xl">
          <div className="flex items-center justify-between p-4">
            <BaseDialog.Title className="sr-only">Screen details</BaseDialog.Title>
            <BaseDialog.Close
              aria-label="Close details"
              className="text-muted-foreground hover:bg-accent hover:text-foreground grid size-9 cursor-pointer place-items-center rounded-lg"
            >
              <X className="size-5" />
            </BaseDialog.Close>
          </div>

          <Tabs defaultValue="information" className="min-h-0 flex-1 gap-0">
            <TabsList className="px-4">
              <TabsTrigger value="information">Information</TabsTrigger>
              <TabsTrigger value="history">History</TabsTrigger>
              <TabsTrigger value="screenshots">Screenshots</TabsTrigger>
              <TabsIndicator />
            </TabsList>

            <div className="min-h-0 flex-1 overflow-y-auto px-5 py-2">
              <TabsPanel value="information">
                <Row label="Last seen" value={dateTime(screen.last_seen)} />
                <Row label="Status" value={screen.last_error ? 'Error' :'OK'} />
                <Row label="Orientation" value={`${screen.orientation ?? 0}° (${screen.orientation_source === 'manual' ?'set by you' :'auto-detected'})`} />
                <Row label="Manufacturer" value={screen.manufacturer} />
                <Row label="Model" value={screen.model} />
                <Row label="Android" value={screen.android_version ? `${screen.android_version} (API ${screen.sdk_int})` : null} />
                <Row label="Resolution" value={screen.screen_width ? `${screen.screen_width}×${screen.screen_height}` : null} />
                <Row label="Storage total" value={screen.total_storage_mb ? `${screen.total_storage_mb} MB` : null} />
                <Row label="Storage free" value={screen.free_storage_mb ? `${screen.free_storage_mb} MB` : null} />
                <Row label="Memory" value={screen.total_ram_mb ? `${screen.total_ram_mb} MB` : null} />
                <Row label="Network" value={screen.network_type} />
                <Row label="Timezone" value={screen.timezone} />
                <Row label="Player version" value={screen.app_version} />
                <Row label="Device id" value={screen.device_id ? <code className="text-xs">{screen.device_id}</code> : null} />
                {/* What an installer types on the remote after Up, Up, Down, Down, OK. */}
                <Row
                  label="Maintenance pin"
                  value={screen.maintenance_pin ? <code className="text-xs">{screen.maintenance_pin}</code> : null}
                />
              </TabsPanel>

              <TabsPanel value="history">
                <Row label="Playback state" value={<span className="capitalize">{screen.playback_state}</span>} />
                <Row label="Last error" value={screen.last_error} />
                <Row label="Last error at" value={screen.last_error_at ? dateTime(screen.last_error_at) : '—'} />
                {!screen.last_error && (
                  <p className="text-muted-foreground py-6 text-sm">No faults reported by this screen.</p>
                )}
              </TabsPanel>

              <TabsPanel value="screenshots">
                <div className="flex justify-end py-3">
                  <Button size="sm" variant="outline" disabled={requestShot.isPending} onClick={() => requestShot.mutate()}>
                    <Camera data-icon="inline-start" /> {requestShot.isPending ? 'Requesting…' :'Request screenshot'}
                  </Button>
                </div>
                {screenshotsQuery.isLoading ? (
                  <div className="space-y-4">{Array.from({ length: 2 }).map((_, index) => <Skeleton key={index} className="aspect-video" />)}</div>
                ) : !screenshots.length ? (
                  <EmptyState icon={Camera} title="No screenshots yet" description="Request one to confirm what this display is actually showing." />
                ) : (
                  <div className="space-y-4 pb-4">
                    {screenshots.map((shot) => (
                      <figure key={shot.id} className="border-hairline bg-muted overflow-hidden rounded-xl border">
                        {/* eslint-disable-next-line @next/next/no-img-element -- player uploads are arbitrary remote URLs, not build-time assets */}
                        <img src={shot.url} alt={`Screen capture taken ${relativeTime(shot.created_at)}`} className="aspect-video w-full object-cover" />
                        <figcaption className="bg-card text-muted-foreground p-2 text-xs">{relativeTime(shot.created_at)}</figcaption>
                      </figure>
                    ))}
                  </div>
                )}
              </TabsPanel>
            </div>
          </Tabs>
        </BaseDialog.Popup>
      </BaseDialog.Portal>
    </BaseDialog.Root>
  )
}
