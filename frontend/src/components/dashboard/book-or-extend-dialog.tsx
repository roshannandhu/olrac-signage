'use client'

import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { CalendarRange, Check, MonitorPlay, Plus } from 'lucide-react'
import { api } from '@/lib/api'
import { rupees } from '@/lib/format'
import { invalidateBookingViews } from '@/lib/query-keys'
import type { ContentItem, Placement, Screen } from '@/lib/types'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { CreateBookingModal } from '@/components/dashboard/create-booking-modal'

/**
 * Putting an advert on a screen when it may already be sold.
 *
 * The "+" beside a creative used to open Create New Booking unconditionally, which is right
 * for a first sale and wrong for every one after it. One advert sold once to one client is
 * ONE booking with several locations; making a second booking for the same sale charges the
 * client twice on the invoice, lists the campaign twice on their report, and — the quiet one
 * — spends a second ad slot out of the workspace's quota, so a tenant allowed ten slots hits
 * the cap at three real campaigns and cannot see why.
 *
 * So: look first, then ask. Never sold → straight through, no extra click. Already running →
 * offer to add these screens to the booking that exists, with "a separate new booking" kept
 * one click away for the case where it genuinely is a different advertiser.
 */
export function BookOrExtendDialog({
  content,
  screens,
  open,
  onOpenChange,
}: {
  content: ContentItem
  /** The screens showing this loop — what "add it here" means on this page. */
  screens: Screen[]
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const queryClient = useQueryClient()
  // Set by a click, never derived: the operator saying "no, this is a different sale".
  const [startNew, setStartNew] = useState(false)
  const [daysOverride, setDaysOverride] = useState('')

  const placementsQuery = useQuery({
    queryKey: ['placements', content.id],
    queryFn: () => api.getPlacements(content.id),
    enabled: open,
  })

  // A booking worth extending is one that has not finished. Extending a campaign that ended
  // last month would backdate the new location into a run nobody is paying for.
  //
  // "Now" is the moment the bookings were fetched, not Date.now() during render: reading the
  // clock while rendering is impure (React flags it, and the same render can then produce
  // two different answers). dataUpdatedAt is a plain number that changes only when the data
  // does, which is also the honest reading -- this list is as fresh as the response it came
  // from, and a refetch re-evaluates it.
  const asOf = placementsQuery.dataUpdatedAt
  const live = useMemo(
    () =>
      (placementsQuery.data ?? []).filter((placement) => {
        const finishes = placement.effective_ends_at ?? placement.ends_at
        return finishes ? new Date(finishes).getTime() >= asOf : true
      }),
    [placementsQuery.data, asOf],
  )

  const finishedCount = (placementsQuery.data?.length ?? 0) - live.length

  const close = (next: boolean) => {
    if (!next) {
      setStartNew(false)
      setDaysOverride('')
    }
    onOpenChange(next)
  }

  const addTargets = useMutation({
    mutationFn: async ({ placement, targets }: { placement: Placement; targets: Screen[] }) => {
      const days = Number(daysOverride)
      // One at a time, not Promise.all: the screen cap and the plan's location limit are
      // checked per call, and firing them together turns "the 4th screen is over your plan"
      // into three successes and one confusing failure in an unpredictable order.
      for (const screen of targets) {
        await api.addPlacementTarget(placement.id, {
          screen_id: screen.id,
          // Omitted by default so the location follows the campaign's own end date. Sent
          // only when the operator typed a different run length for these screens.
          ...(days > 0 ? { days } : {}),
        })
      }
      return targets.length
    },
    onSuccess: (count, { placement }) => {
      invalidateBookingViews(queryClient)
      queryClient.invalidateQueries({ queryKey: ['placements', content.id] })
      toast.success(
        `${count} screen${count === 1 ? '' : 's'} added to ${placement.advertiser}'s booking.`,
      )
      close(false)
    },
    // The backend refuses over the plan's location cap with a message naming the plan and
    // the limit, so show what it said rather than a generic failure.
    onError: (error: Error) => toast.error(error.message),
  })

  if (!open) return null

  // Deciding needs the answer. Showing the booking form first and swapping it underneath the
  // operator would be worse than a moment's wait.
  if (placementsQuery.isLoading) {
    return (
      <Dialog open onOpenChange={close}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Checking this advert…</DialogTitle>
            <DialogDescription>Looking for a booking it already belongs to.</DialogDescription>
          </DialogHeader>
        </DialogContent>
      </Dialog>
    )
  }

  // Never sold, or the operator chose a separate sale: the original behaviour, unchanged.
  if (startNew || live.length === 0) {
    return (
      <CreateBookingModal
        open
        onOpenChange={close}
        contentId={content.id}
        contentTitle={content.name}
        defaultScreenIds={screens.map((screen) => screen.id)}
        initialClientId={content.client_id ?? null}
        initialAdvertiser={content.client_name ?? ''}
      />
    )
  }

  return (
    <Dialog open onOpenChange={close}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>This advert is already running</DialogTitle>
          <DialogDescription>
            Add these screens to the booking it belongs to, so it stays one campaign on the
            invoice and on the client&apos;s report.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          {live.map((placement) => {
            // A screen counts as already covered if the booking names it directly OR names a
            // group it belongs to — a group target puts the advert on every screen inside it,
            // and offering to add one of those again would book it twice on the same panel.
            const bookedScreenIds = new Set(
              placement.targets.filter((t) => t.screen_id).map((t) => t.screen_id),
            )
            const bookedGroupIds = new Set(
              placement.targets.filter((t) => t.kind === 'group' && t.group_id).map((t) => t.group_id),
            )
            const missing = screens.filter(
              (screen) =>
                !bookedScreenIds.has(screen.id) &&
                !(screen.group_id && bookedGroupIds.has(screen.group_id)),
            )
            const finishes = placement.effective_ends_at ?? placement.ends_at

            return (
              <div key={placement.id} className="rounded-xl border border-hairline p-3.5">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="font-semibold text-foreground">{placement.advertiser}</p>
                  <p className="text-sm text-muted-foreground">
                    {rupees(placement.total_price_paise ?? placement.price_paise)}
                  </p>
                </div>
                <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                  <span className="inline-flex items-center gap-1">
                    <CalendarRange className="size-3" />
                    until {finishes ? new Date(finishes).toLocaleDateString() : 'no end date'}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <MonitorPlay className="size-3" />
                    {placement.screens_used} screen{placement.screens_used === 1 ? '' : 's'}
                  </span>
                </p>

                {missing.length === 0 ? (
                  <p className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-emerald-500/10 px-2.5 py-1.5 text-xs text-emerald-600 dark:text-emerald-400">
                    <Check className="size-3.5" />
                    Already running on {screens.length === 1 ? 'this screen' : 'these screens'}
                  </p>
                ) : (
                  <Button
                    size="sm"
                    className="mt-3"
                    disabled={addTargets.isPending}
                    onClick={() => addTargets.mutate({ placement, targets: missing })}
                  >
                    <Plus />
                    Add {missing.length === 1 ? 'this screen' : `${missing.length} screens`} to it
                  </Button>
                )}
              </div>
            )
          })}

          <div className="space-y-1.5">
            <Label htmlFor="extend-days" className="text-xs">
              Run length for the added screens (optional)
            </Label>
            <Input
              id="extend-days"
              type="number"
              min={1}
              placeholder="Follows the campaign's end date"
              value={daysOverride}
              onChange={(event) => setDaysOverride(event.target.value)}
            />
            <p className="text-xs text-muted-foreground/70">
              Leave empty and the new screens finish with the campaign. Set a number to sell
              them their own run — &ldquo;30 days in the mall, 10 in the shop&rdquo;.
            </p>
          </div>
        </div>

        <div className="mt-2 border-t border-hairline pt-3">
          <Button variant="outline" className="w-full" onClick={() => setStartNew(true)}>
            Create a separate new booking
          </Button>
          <p className="mt-1.5 text-center text-xs text-muted-foreground/70">
            For a different advertiser buying the same creative.
            {finishedCount > 0 && ` ${finishedCount} earlier booking${finishedCount === 1 ? ' has' : 's have'} already finished.`}
          </p>
        </div>
      </DialogContent>
    </Dialog>
  )
}
