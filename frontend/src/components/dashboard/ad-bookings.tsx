'use client'

import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { CalendarRange, FileDown, Layers3, MonitorPlay, Plus, Receipt, Trash2, X } from 'lucide-react'
import { EmptyState } from '@/components/dashboard/empty-state'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import { canEditTenantContent } from '@/lib/roles'
import { useAuthStore } from '@/lib/store'
import type { Placement, PlacementTarget, Screen, ScreenGroup } from '@/lib/types'

const rupees = (paise: number) => `₹${(paise / 100).toLocaleString('en-IN')}`
const asDate = (iso: string) => new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })

function runState(placement: Placement): { label: string; tone: 'success' | 'warning' | 'outline' } {
  const now = Date.now()
  if (Date.parse(placement.starts_at) > now) return { label: 'Scheduled', tone: 'warning' }
  if (Date.parse(placement.ends_at) < now) return { label: 'Ended', tone: 'outline' }
  return { label: 'Running', tone: 'success' }
}

/**
 * Selling this advert: who bought it, for how long, and in which places.
 *
 * Adding or removing a place here writes straight through to that screen's or group's
 * playlist, so the loop on the wall and the deal on the books can never disagree.
 */
export function AdBookings({ contentId }: { contentId: number }) {
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)
  const canEdit = canEditTenantContent(user)

  const placementsQuery = useQuery({ queryKey: ['placements', contentId], queryFn: () => api.getPlacements(contentId) })
  const screensQuery = useQuery({ queryKey: ['screens'], queryFn: api.getScreens })
  const groupsQuery = useQuery({ queryKey: ['groups'], queryFn: api.getGroups })

  const placements = placementsQuery.data || []
  const screens = useMemo(() => (screensQuery.data || []) as Screen[], [screensQuery.data])
  const groups = useMemo(() => (groupsQuery.data || []) as ScreenGroup[], [groupsQuery.data])

  const [createOpen, setCreateOpen] = useState(false)
  const [advertiser, setAdvertiser] = useState('')
  const [price, setPrice] = useState('')
  // Lazy initialisers: reading the clock during render is impure and would drift on
  // every re-render.
  const [startsAt, setStartsAt] = useState(() => new Date().toISOString().slice(0, 10))
  const [endsAt, setEndsAt] = useState(() => new Date(Date.now() + 30 * 864e5).toISOString().slice(0, 10))
  const [picked, setPicked] = useState<string[]>([])

  const [addTo, setAddTo] = useState<Placement | null>(null)
  const [splitting, setSplitting] = useState<{ placement: Placement; target: PlacementTarget } | null>(null)
  const [excluded, setExcluded] = useState<number[]>([])

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['placements', contentId] })
    queryClient.invalidateQueries({ queryKey: ['playlists'] })
    queryClient.invalidateQueries({ queryKey: ['screens'] })
    queryClient.invalidateQueries({ queryKey: ['groups'] })
  }
  const fail = (error: Error) => toast.error(error.message)

  const create = useMutation({
    mutationFn: () => api.createPlacement({
      content_id: contentId,
      advertiser: advertiser.trim(),
      // Rupees in the box, paise on the wire — money never rides on a float.
      price_paise: Math.round(Number(price || 0) * 100),
      is_paid: false,
      starts_at: new Date(`${startsAt}T00:00:00`).toISOString(),
      ends_at: new Date(`${endsAt}T23:59:59`).toISOString(),
      targets: picked.map((key) => key.startsWith('s') ? { screen_id: Number(key.slice(1)) } : { group_id: Number(key.slice(1)) }),
    }),
    onSuccess: () => {
      refresh(); toast.success('Booking created and placed')
      setCreateOpen(false); setAdvertiser(''); setPrice(''); setPicked([])
    },
    onError: fail,
  })

  const removeTarget = useMutation({
    mutationFn: ({ id, targetId }: { id: number; targetId: number }) => api.removePlacementTarget(id, targetId),
    onSuccess: () => { refresh(); toast.success('Removed from that place') },
    onError: fail,
  })

  const addTarget = useMutation({
    mutationFn: ({ id, key }: { id: number; key: string }) =>
      api.addPlacementTarget(id, key.startsWith('s') ? { screen_id: Number(key.slice(1)) } : { group_id: Number(key.slice(1)) }),
    onSuccess: () => { refresh(); toast.success('Added to that place') },
    onError: fail,
  })

  const split = useMutation({
    mutationFn: () => api.splitPlacementTarget(splitting!.placement.id, splitting!.target.id, excluded),
    onSuccess: () => { refresh(); toast.success('Booking now targets the remaining screens'); setSplitting(null); setExcluded([]) },
    onError: fail,
  })

  const togglePaid = useMutation({
    mutationFn: (p: Placement) => api.updatePlacement(p.id, { is_paid: !p.is_paid }),
    onSuccess: () => { refresh() },
    onError: fail,
  })

  const remove = useMutation({
    mutationFn: (id: number) => api.deletePlacement(id),
    onSuccess: () => { refresh(); toast.success('Booking deleted and pulled from every place') },
    onError: fail,
  })

  const placeOptions = [
    ...groups.map((g) => ({ key: `g${g.id}`, label: g.name, kind: 'group' as const })),
    ...screens.map((s) => ({ key: `s${s.id}`, label: s.name || `Screen ${s.id}`, kind: 'screen' as const })),
  ]

  if (placementsQuery.isLoading) {
    return <div className="space-y-3">{Array.from({ length: 2 }).map((_, i) => <Skeleton key={i} className="h-32 rounded-xl" />)}</div>
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-muted-foreground text-sm">
          Sell this advert to a client for a period and a set of places. Removing a place takes it off that screen straight away.
        </p>
        {canEdit && <Button onClick={() => setCreateOpen(true)}><Plus data-icon="inline-start" /> New booking</Button>}
      </div>

      {!placements.length ? (
        <EmptyState
          icon={Receipt}
          title="Not sold to anyone yet"
          description="Create a booking to record who is paying for this advert, for how long, and where it should run."
          action={canEdit ? <Button onClick={() => setCreateOpen(true)}>New booking</Button> : undefined}
        />
      ) : placements.map((placement) => {
        const state = runState(placement)
        return (
          <Card key={placement.id} className="ring-hairline bg-card border-0 ring-1">
            <CardContent className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-foreground font-semibold">{placement.advertiser}</h3>
                    <Badge variant={state.tone}>{state.label}</Badge>
                    {placement.price_paise > 0 && (
                      <Badge variant={placement.is_paid ? 'success' : 'warning'}>
                        {rupees(placement.price_paise)} · {placement.is_paid ? 'paid' : 'unpaid'}
                      </Badge>
                    )}
                  </div>
                  <p className="text-muted-foreground mt-1 flex items-center gap-1.5 text-sm">
                    <CalendarRange className="size-3.5" aria-hidden="true" />
                    {asDate(placement.starts_at)} → {asDate(placement.ends_at)}
                  </p>
                </div>
                {canEdit && (
                  <div className="flex items-center gap-2">
                    {placement.price_paise > 0 && (
                      <Button size="sm" variant="outline" onClick={() => togglePaid.mutate(placement)}>
                        Mark {placement.is_paid ? 'unpaid' : 'paid'}
                      </Button>
                    )}
                    <Button size="sm" variant="outline" render={
                      // A plain link so the browser handles the download; the API sets the
                      // filename from the client's name.
                      <a href={api.bookingReportPdfUrl(placement.id)} target="_blank" rel="noreferrer" />
                    }>
                      <FileDown data-icon="inline-start" /> Report
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => setAddTo(placement)}>
                      <Plus data-icon="inline-start" /> Add places
                    </Button>
                    <Button size="sm" variant="ghost" className="text-destructive" onClick={() => remove.mutate(placement.id)} aria-label={`Delete booking for ${placement.advertiser}`}>
                      <Trash2 />
                    </Button>
                  </div>
                )}
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                {!placement.targets.length && <p className="text-muted-foreground text-sm">Not running anywhere yet.</p>}
                {placement.targets.map((target) => (
                  <span
                    key={target.id}
                    className={`ring-hairline inline-flex items-center gap-1.5 rounded-lg py-1.5 pr-1.5 pl-2.5 text-sm ring-1 ${target.is_placed ? 'bg-secondary/60' : 'bg-muted/40 opacity-70'}`}
                  >
                    {target.kind === 'group'
                      ? <Layers3 className="text-primary dark:text-brand size-3.5" aria-hidden="true" />
                      : <MonitorPlay className="text-primary dark:text-brand size-3.5" aria-hidden="true" />}
                    {target.name}
                    {!target.is_placed && <span className="text-muted-foreground text-xs">(removed by hand)</span>}
                    {canEdit && (
                      <button
                        onClick={() => target.kind === 'group'
                          ? setSplitting({ placement, target })
                          : removeTarget.mutate({ id: placement.id, targetId: target.id })}
                        aria-label={`Stop playing on ${target.name}`}
                        className="hover:bg-destructive/10 hover:text-destructive grid size-6 cursor-pointer place-items-center rounded"
                      >
                        <X className="size-3.5" />
                      </button>
                    )}
                  </span>
                ))}
              </div>
            </CardContent>
          </Card>
        )
      })}

      {/* New booking */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>New booking</DialogTitle>
            <DialogDescription>Record who is paying for this advert and where it should run.</DialogDescription>
          </DialogHeader>
          <div className="max-h-[55vh] space-y-4 overflow-y-auto px-1 pt-2">
            <div className="space-y-2">
              <Label htmlFor="advertiser">Client</Label>
              <Input id="advertiser" value={advertiser} onChange={(e) => setAdvertiser(e.target.value)} placeholder="Pittappillil Agencies" autoFocus />
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="space-y-2">
                <Label htmlFor="price">Price (₹)</Label>
                <Input id="price" type="number" min={0} value={price} onChange={(e) => setPrice(e.target.value)} placeholder="50000" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="from">From</Label>
                <Input id="from" type="date" value={startsAt} onChange={(e) => setStartsAt(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="to">Until</Label>
                <Input id="to" type="date" value={endsAt} onChange={(e) => setEndsAt(e.target.value)} />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Where it plays</Label>
              <div className="border-hairline max-h-52 space-y-1 overflow-y-auto rounded-xl border p-2">
                {placeOptions.map((option) => (
                  <label key={option.key} className="hover:bg-muted flex cursor-pointer items-center gap-3 rounded-lg p-2 text-sm">
                    <input
                      type="checkbox"
                      className="accent-primary size-4"
                      checked={picked.includes(option.key)}
                      onChange={(e) => setPicked((cur) => e.target.checked ? [...cur, option.key] : cur.filter((k) => k !== option.key))}
                    />
                    {option.kind === 'group' ? <Layers3 className="size-3.5" /> : <MonitorPlay className="size-3.5" />}
                    <span className="flex-1">{option.label}</span>
                    {option.kind === 'group' && <Badge variant="secondary">group</Badge>}
                  </label>
                ))}
                {!placeOptions.length && <p className="text-muted-foreground p-2 text-sm">No screens or groups yet.</p>}
              </div>
              <p className="text-muted-foreground text-xs">Choosing a group runs the advert on every screen in it.</p>
            </div>
          </div>
          <DialogFooter showCloseButton>
            <Button disabled={!advertiser.trim() || !picked.length || endsAt <= startsAt || create.isPending} onClick={() => create.mutate()}>
              {create.isPending ? 'Creating…' : 'Create booking'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add more places to an existing booking */}
      <Dialog open={Boolean(addTo)} onOpenChange={(open) => !open && setAddTo(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add places</DialogTitle>
            <DialogDescription>Where else should {addTo?.advertiser}&apos;s advert run?</DialogDescription>
          </DialogHeader>
          <div className="max-h-[55vh] space-y-1 overflow-y-auto px-1 pt-2">
            {placeOptions
              .filter((option) => !addTo?.targets.some((t) => option.key === (t.kind === 'group' ? `g${t.group_id}` : `s${t.screen_id}`)))
              .map((option) => (
                <button
                  key={option.key}
                  onClick={() => { addTarget.mutate({ id: addTo!.id, key: option.key }); setAddTo(null) }}
                  className="hover:bg-muted flex w-full cursor-pointer items-center gap-3 rounded-lg p-2.5 text-left text-sm"
                >
                  {option.kind === 'group' ? <Layers3 className="size-4" /> : <MonitorPlay className="size-4" />}
                  <span className="flex-1">{option.label}</span>
                  <Plus className="size-4" />
                </button>
              ))}
          </div>
        </DialogContent>
      </Dialog>

      {/* Removing one screen from a group booking */}
      <Dialog open={Boolean(splitting)} onOpenChange={(open) => { if (!open) { setSplitting(null); setExcluded([]) } }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>This advert is booked on a whole group</DialogTitle>
            <DialogDescription>
              A group booking puts one entry in the shared group playlist, so it cannot be removed from a single screen.
              Pick the screens it should stop playing on and the booking will target the remaining ones individually.
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-[45vh] space-y-1 overflow-y-auto px-1 pt-2">
            {screens.filter((s) => s.group_id === splitting?.target.group_id).map((screen) => (
              <label key={screen.id} className="hover:bg-muted flex cursor-pointer items-center gap-3 rounded-lg p-2.5 text-sm">
                <input
                  type="checkbox"
                  className="accent-destructive size-4"
                  checked={excluded.includes(screen.id)}
                  onChange={(e) => setExcluded((cur) => e.target.checked ? [...cur, screen.id] : cur.filter((id) => id !== screen.id))}
                />
                <span className="flex-1">{screen.name || `Screen ${screen.id}`}</span>
                {excluded.includes(screen.id) && <Badge variant="danger">stops playing</Badge>}
              </label>
            ))}
          </div>
          <DialogFooter showCloseButton>
            <Button
              variant="outline"
              onClick={() => { removeTarget.mutate({ id: splitting!.placement.id, targetId: splitting!.target.id }); setSplitting(null) }}
            >
              Remove from the whole group
            </Button>
            <Button disabled={!excluded.length || split.isPending} onClick={() => split.mutate()}>
              {split.isPending ? 'Updating…' : 'Keep the rest'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
