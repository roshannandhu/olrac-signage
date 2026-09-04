'use client'

import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { Building2, CalendarRange, Layers3, Receipt } from 'lucide-react'
import { ErrorState } from '@/components/dashboard/error-state'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import { asDate, bookingState, rupees } from '@/lib/format'

/** Matches MAX_GROUP_DEPTH in the backend, which walks the same chain. */
const MAX_GROUP_DEPTH = 32

/**
 * Adverts sold onto this screen.
 *
 * A booking already reaches the screen correctly -- it becomes a real playlist item -- but
 * the screen page never said so. It showed up inside the loop as an unnamed row labelled
 * only "Scheduled", with no client, no dates and no price, so an operator who sold
 * "Brightmart, 30 days, Screen 5" and then opened Screen 5 saw no sign of it. That reads
 * as the booking not having worked.
 *
 * Read-only on purpose: this is the screen's point of view on a commercial record that
 * belongs to the advert. Editing lives on the ad detail page each row links to. AdBookings
 * is deliberately not reused here -- it is content-scoped and a full write surface.
 *
 * No endpoint of its own: /placements/ is already fetched and cached under
 * ['all-placements'] by the campaigns page, and carries every target's screen, group and
 * window. Filtering it here costs nothing; another round trip to the database's region
 * would cost ~114 ms.
 */
export function ScreenAdBookings({ screenId, groupId }: { screenId: number; groupId: number | null }) {
  const placementsQuery = useQuery({ queryKey: ['all-placements'], queryFn: api.getAllPlacements })
  const groupsQuery = useQuery({ queryKey: ['groups'], queryFn: api.getGroups })

  // Every group this screen inherits from, nearest first. A booking sold to a parent group
  // reaches this screen just as much as one sold to it directly, and not showing those
  // would recreate the same blind spot one level up.
  const groupChain = useMemo(() => {
    const byId = new Map((groupsQuery.data || []).map((group) => [group.id, group]))
    const chain = new Map<number, string>()
    let current = groupId
    for (let hop = 0; hop < MAX_GROUP_DEPTH && current != null && !chain.has(current); hop += 1) {
      const group = byId.get(current)
      chain.set(current, group?.name || `Group ${current}`)
      current = group?.parent_id ?? null
    }
    return chain
  }, [groupsQuery.data, groupId])

  const booked = useMemo(() => {
    // ponytail: static groups only. A dynamic group's playlist can reach this screen too,
    // but nothing links one to a screen client-side; add the criteria match here if
    // dynamic groups ever get a UI.
    return (placementsQuery.data || []).flatMap((placement) => {
      const target = placement.targets.find(
        (candidate) =>
          candidate.screen_id === screenId
          || (candidate.group_id != null && groupChain.has(candidate.group_id)),
      )
      return target ? [{ placement, target }] : []
    })
  }, [placementsQuery.data, screenId, groupChain])

  if (placementsQuery.isError) {
    return (
      <ErrorState
        message="Bookings on this screen could not be loaded."
        onRetry={() => placementsQuery.refetch()}
      />
    )
  }

  if (placementsQuery.isLoading) {
    return <Skeleton className="h-32 rounded-2xl" />
  }

  return (
    <section className="ring-hairline bg-card rounded-2xl p-5 shadow-sm ring-1">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-foreground flex items-center gap-2 font-semibold">
          <Receipt className="text-primary dark:text-brand size-4" aria-hidden="true" />
          Adverts booked on this screen
        </h2>
        {booked.length > 0 && (
          <span className="text-muted-foreground text-sm tabular-nums">
            {booked.length} booking{booked.length === 1 ? '' : 's'}
          </span>
        )}
      </div>

      {booked.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          No adverts are sold onto this screen. Bookings made against it, or against a group
          it belongs to, will appear here.
        </p>
      ) : (
        <div className="divide-hairline divide-y">
          {booked.map(({ placement, target }) => {
            const state = bookingState(placement)
            const from = target.starts_at || placement.starts_at
            const until = target.ends_at || placement.effective_ends_at || placement.ends_at
            const viaGroup = target.group_id != null ? groupChain.get(target.group_id) : null
            return (
              <Link
                key={`${placement.id}-${target.id}`}
                href={`/dashboard/content/${placement.content_id}`}
                className="hover:bg-muted/50 -mx-2 flex flex-col gap-3 rounded-lg px-2 py-3.5 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex min-w-0 flex-1 items-center gap-2.5">
                  <span className="bg-primary/10 text-primary dark:text-brand grid size-8 shrink-0 place-items-center rounded-lg">
                    {viaGroup
                      ? <Layers3 className="size-4" aria-hidden="true" />
                      : <Building2 className="size-4" aria-hidden="true" />}
                  </span>
                  <div className="min-w-0">
                    <p className="text-foreground truncate text-sm font-medium">
                      {placement.advertiser}
                    </p>
                    <p className="text-muted-foreground flex flex-wrap items-center gap-x-1.5 text-xs">
                      <CalendarRange className="size-3" aria-hidden="true" />
                      {asDate(from)} → {asDate(until)}
                      {target.days != null && <span className="tabular-nums">· {target.days}d here</span>}
                      {viaGroup && <span className="truncate">· via {viaGroup}</span>}
                    </p>
                  </div>
                </div>

                <div className="flex shrink-0 flex-wrap items-center gap-2">
                  {!target.is_placed && <Badge variant="warning">Removed by hand</Badge>}
                  <Badge variant={placement.is_paid ? 'success' : 'outline'}>
                    {placement.is_paid ? 'Paid' : 'Unpaid'}
                  </Badge>
                  <Badge variant={state.tone}>{state.label}</Badge>
                  <span className="text-foreground text-sm font-medium tabular-nums">
                    {rupees(placement.total_price_paise ?? placement.price_paise)}
                  </span>
                </div>
              </Link>
            )
          })}
        </div>
      )}
    </section>
  )
}
