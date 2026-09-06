'use client'

import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { ArrowUpCircle, CalendarRange, FileDown, IndianRupee, Layers3, Mail, MonitorPlay, MoreHorizontal, Plus, Receipt, Share2, Trash2, X } from 'lucide-react'
import { EmptyState } from '@/components/dashboard/empty-state'
import { ErrorState } from '@/components/dashboard/error-state'
import { EmailReportModal } from '@/components/dashboard/email-report-modal'
import { CreateBookingModal } from '@/components/dashboard/create-booking-modal'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import { canEditTenantContent } from '@/lib/roles'
import { useAuthStore } from '@/lib/store'
import type { PaymentMethod, Placement, PlacementTarget, PlanOption, Screen, ScreenGroup } from '@/lib/types'
import { addDays, asDate, bookingState, dateInput, money, rupees } from '@/lib/format'
import { invalidateBookingViews } from '@/lib/query-keys'

// The same words the invoices page and the invoice PDF use for a method.
const METHOD_LABELS: Record<PaymentMethod, string> = {
  cash: 'Cash', upi: 'UPI', bank_transfer: 'Bank transfer',
  cheque: 'Cheque', card: 'Card', other: 'Other',
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
  const clientsQuery = useQuery({ queryKey: ['clients'], queryFn: api.getClients })
  // Active only: a retired plan should not be sellable, but bookings already on one keep
  // naming it, which is why the API retires rather than deletes.
  const tenantPlansQuery = useQuery({ queryKey: ['tenant-plans'], queryFn: () => api.getTenantPlans() })

  const placements = placementsQuery.data || []
  const screens = useMemo(() => (screensQuery.data || []) as Screen[], [screensQuery.data])
  const groups = useMemo(() => (groupsQuery.data || []) as ScreenGroup[], [groupsQuery.data])
  const clients = clientsQuery.data || []
  const plans = tenantPlansQuery.data || []

  // The PDF is built per request and never stored, so both buttons are a fetch that can
  // take a second or two on a long campaign. Tracked per placement rather than globally so
  // one report generating does not disable the buttons on every other row.
  const [busyReport, setBusyReport] = useState<number | null>(null)

  const runReport = async (placement: Placement, mode: 'share' | 'download' | 'invoice') => {
    setBusyReport(placement.id)
    try {
      if (mode === 'invoice') {
        await api.downloadInvoice(placement.id)
      } else if (mode === 'download') {
        await api.downloadBookingReport(placement.id)
      } else {
        const outcome = await api.shareBookingReport(placement.id, `Playback report — ${placement.advertiser}`)
        // Saying "shared" when the browser could not share would be a lie the operator
        // acts on -- they would tell the client it had been sent.
        if (outcome === 'downloaded') {
          toast.info('Sharing is not available in this browser, so the report was downloaded instead.')
        }
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'The report could not be generated.')
    } finally {
      setBusyReport(null)
    }
  }

  const [createOpen, setCreateOpen] = useState(false)
  const [emailPlacement, setEmailPlacement] = useState<Placement | null>(null)

  const [addTo, setAddTo] = useState<Placement | null>(null)
  const [splitting, setSplitting] = useState<{ placement: Placement; target: PlacementTarget } | null>(null)
  const [excluded, setExcluded] = useState<number[]>([])

  const refresh = () => invalidateBookingViews(queryClient)
  const fail = (error: Error) => toast.error(error.message)

  const [extending, setExtending] = useState<Placement | null>(null)
  const [extendTo, setExtendTo] = useState('')
  const [extendPrice, setExtendPrice] = useState('')

  const [deleting, setDeleting] = useState<Placement | null>(null)

  // --- Changing a client's plan -------------------------------------------------------
  const [upgrading, setUpgrading] = useState<Placement | null>(null)
  // `null` is now a plan choice of its own -- "off the package, on a negotiated price" --
  // so "nothing chosen yet" cannot also be null. undefined is that.
  const [chosenPlan, setChosenPlan] = useState<number | null | undefined>(undefined)
  const [alsoExtend, setAlsoExtend] = useState(true)
  const planOptionsQuery = useQuery({
    queryKey: ['plan-options', upgrading?.id],
    queryFn: () => api.getPlanOptions(upgrading!.id),
    enabled: Boolean(upgrading),
  })

  const openUpgrade = (placement: Placement) => {
    setUpgrading(placement)
    setChosenPlan(undefined)
    setAlsoExtend(true)
  }

  const upgrade = useMutation({
    mutationFn: () => api.upgradePlan(upgrading!.id, {
      plan_id: chosenPlan ?? null,
      // Meaningless when coming off a package: there is no plan length to extend BY, and
      // the server ignores it, so the checkbox is hidden rather than sent as a lie.
      extend: chosenPlan != null && alsoExtend,
    }),
    onSuccess: () => {
      refresh()
      toast.success(
        chosenPlan == null
          ? 'Moved off the package; the price is yours to set'
          : alsoExtend ? 'Plan changed and the run extended' : 'Plan changed',
      )
      setUpgrading(null)
    },
    onError: fail,
  })

  // --- Recording what the client paid --------------------------------------------------
  const [paying, setPaying] = useState<Placement | null>(null)
  const [payAmount, setPayAmount] = useState('')
  const [payMethod, setPayMethod] = useState<PaymentMethod>('upi')
  const [payReference, setPayReference] = useState('')
  const [payDate, setPayDate] = useState('')

  const openPayment = (placement: Placement) => {
    setPaying(placement)
    // THIS receipt, not the running total: payments are a ledger and saving adds a row.
    // Prefilled with the outstanding balance, which is what is being handed over almost
    // every time -- and unlike the old running-total box, an operator who types today's
    // instalment out of habit now gets exactly what they meant.
    const last = placement.payments.at(-1)
    setPayAmount(String(money(placement).balance / 100))
    setPayMethod(last?.method ?? 'upi')
    setPayReference('')
    setPayDate(dateInput(new Date()))
  }

  const savePayment = useMutation({
    mutationFn: () => api.recordPayment(paying!.id, {
      amount_paise: Math.round(Number(payAmount || 0) * 100),
      method: payMethod,
      reference: payReference.trim() || null,
      paid_at: new Date(`${payDate}T12:00:00`).toISOString(),
    }),
    onSuccess: () => { refresh(); toast.success('Payment recorded'); setPaying(null) },
    onError: fail,
  })

  const clearPayment = useMutation({
    mutationFn: () => api.clearPayment(paying!.id),
    onSuccess: () => { refresh(); toast.success('Every receipt cleared; the booking is unpaid again'); setPaying(null) },
    onError: fail,
  })

  // One receipt out. The rest stand, so pulling a duplicate does not un-pay the deposit
  // that really was taken -- and it is how a mistyped amount gets corrected, since a
  // receipt is never edited in place.
  const deletePayment = useMutation({
    mutationFn: (paymentId: number) => api.deletePayment(paying!.id, paymentId),
    onSuccess: () => { refresh(); toast.success('Receipt removed'); setPaying(null) },
    onError: fail,
  })

  const openExtend = (placement: Placement) => {
    setExtending(placement)
    // Default to a fortnight past wherever the run currently finishes, so the common case
    // is one click and a price. extended_from defaults server side to the same point,
    // which is what stops an unpaid gap opening mid-campaign.
    const from = Date.parse(placement.effective_ends_at || placement.ends_at)
    setExtendTo(dateInput(from + 15 * 864e5))
    setExtendPrice('')
  }

  const extend = useMutation({
    mutationFn: () => api.addPlacementExtension(extending!.id, {
      extended_to: new Date(`${extendTo}T23:59:59`).toISOString(),
      additional_price_paise: Math.round(Number(extendPrice || 0) * 100),
      is_paid: false,
    }),
    onSuccess: () => { refresh(); toast.success('Booking extended'); setExtending(null) },
    onError: fail,
  })

  const dropExtension = useMutation({
    mutationFn: ({ id, extensionId }: { id: number; extensionId: number }) =>
      api.removePlacementExtension(id, extensionId),
    onSuccess: () => { refresh(); toast.success('Extension removed and the run pulled back in') },
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

  const remove = useMutation({
    mutationFn: (id: number) => api.deletePlacement(id),
    onSuccess: () => { refresh(); toast.success('Booking deleted and pulled from every place') },
    onError: fail,
  })

  const placeOptions = [
    ...groups.map((g) => ({ key: `g${g.id}`, label: g.name, kind: 'group' as const })),
    ...screens.map((s) => ({ key: `s${s.id}`, label: s.name || `Screen ${s.id}`, kind: 'screen' as const })),
  ]

  // Ordered before the loading branch, and before the empty state below it, because
  // `placements` falls back to [] on failure -- so a request that errored used to render
  // "Not sold to anyone yet" for a paid, running campaign. An operator reading that would
  // sell the slot a second time.
  if (placementsQuery.isError) {
    return (
      <ErrorState
        message="This advert's bookings could not be loaded."
        onRetry={() => placementsQuery.refetch()}
      />
    )
  }

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
        const state = bookingState(placement)
        const bill = money(placement)
        return (
          <Card key={placement.id} className="ring-hairline bg-card border-0 ring-1">
            <CardContent className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-foreground font-semibold">{placement.advertiser}</h3>
                    <Badge variant={state.tone}>{state.label}</Badge>
                    {placement.client && <Badge variant="outline">{placement.client.client_code}</Badge>}
                    {placement.plan && <Badge variant="outline">{placement.plan.name}</Badge>}
                    {/* The TOTAL, not the originally sold price. After an upgrade or an
                        extension those differ, and showing the sold figure read as
                        "₹5,000 · paid" on a booking that owed ₹12,000 and had received
                        ₹5,000 of it. Both halves come from one derivation now, shared with
                        the ad header, the invoices page and the PDF. */}
                    {bill.total > 0 && (
                      <Badge variant={bill.tone === 'outline' ? 'warning' : bill.tone}>
                        {rupees(bill.total)} · {bill.shortLabel}
                      </Badge>
                    )}
                  </div>
                  <p className="text-muted-foreground mt-1 flex items-center gap-1.5 text-sm">
                    <CalendarRange className="size-3.5" aria-hidden="true" />
                    {asDate(placement.starts_at)} → {asDate(placement.ends_at)}
                    {/* starts_at/ends_at stay as SOLD. When an extension moved the finish
                        line, showing only the sold date would tell an operator a running
                        campaign had ended. */}
                    {placement.extensions.length > 0 && placement.effective_ends_at && (
                      <span className="text-foreground">
                        · extended to {asDate(placement.effective_ends_at)}
                        {placement.total_price_paise != null && ` (${rupees(placement.total_price_paise)} total)`}
                      </span>
                    )}
                  </p>
                </div>
                {/* Two actions inline, everything else behind the overflow. Seven controls
                    in one row read as a toolbar with no hierarchy: the two a tenant
                    actually reaches for -- move the client up a plan, take their money --
                    sat between Share and Add places at the same weight. */}
                {canEdit && (
                  <div className="flex shrink-0 items-center gap-2">
                    <Button size="sm" variant="outline" onClick={() => openUpgrade(placement)}>
                      <ArrowUpCircle data-icon="inline-start" /> Change plan
                    </Button>
                    {/* Filled while money is outstanding, part payment included. Reading
                        `is_paid` made a booking with ₹45,000 still owing offer a quiet
                        "Payment" button, as if there were nothing left to collect. */}
                    <Button
                      size="sm"
                      variant={bill.balance > 0 ? 'default' : 'outline'}
                      onClick={() => openPayment(placement)}
                    >
                      <IndianRupee data-icon="inline-start" />
                      {bill.status === 'paid' ? 'Payment' : bill.status === 'part_paid' ? 'Add payment' : 'Record payment'}
                    </Button>
                    <DropdownMenu>
                      <DropdownMenuTrigger
                        render={<Button size="icon-sm" variant="ghost" aria-label={`More actions for ${placement.advertiser}`} />}
                      >
                        <MoreHorizontal />
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuLabel>Documents</DropdownMenuLabel>
                        {/* All three fetch with the auth header. These were once plain
                            <a href> links, which navigate WITHOUT it and 401'd every
                            time -- the report button had never worked. */}
                        <DropdownMenuItem
                          disabled={busyReport === placement.id}
                          onClick={() => runReport(placement, 'download')}
                        >
                          <FileDown data-icon="inline-start" /> Playback report
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          disabled={busyReport === placement.id}
                          onClick={() => runReport(placement, 'invoice')}
                        >
                          <Receipt data-icon="inline-start" /> Invoice
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          disabled={busyReport === placement.id}
                          onClick={() => runReport(placement, 'share')}
                        >
                          <Share2 data-icon="inline-start" /> Share report
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => setEmailPlacement(placement)}>
                          <Mail data-icon="inline-start" /> Email to client
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuLabel>Booking</DropdownMenuLabel>
                        <DropdownMenuItem onClick={() => openExtend(placement)}>
                          <CalendarRange data-icon="inline-start" /> Extend the run
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => setAddTo(placement)}>
                          <Plus data-icon="inline-start" /> Add places
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        {/* Confirmed, unlike before. This deletes the sale AND pulls the
                            advert off every screen it was placed on, and it was the one
                            destructive action in the app that fired on a single click. */}
                        <DropdownMenuItem
                          className="text-destructive"
                          onClick={() => setDeleting(placement)}
                        >
                          <Trash2 data-icon="inline-start" /> Delete booking
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                )}
              </div>

              {/* The money, spelled out. Everything above states a total and a status; the
                  question an operator actually asks -- "how much of this have we been
                  given, and how much is still to come?" -- was answerable only by opening
                  the payment dialog and reading a prefilled box. Three figures, in the
                  order they are asked about. */}
              {bill.total > 0 && (
                <div className="bg-muted/40 ring-hairline mt-4 grid grid-cols-3 gap-3 rounded-xl p-3 ring-1">
                  <div>
                    <p className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">Contract</p>
                    <p className="text-foreground text-sm font-semibold tabular-nums">{rupees(bill.total)}</p>
                    {placement.extensions.length > 0 && (
                      <p className="text-muted-foreground text-[11px]">
                        {rupees(placement.price_paise)} sold + {rupees(bill.total - placement.price_paise)} extended
                      </p>
                    )}
                  </div>
                  <div>
                    <p className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">Received</p>
                    <p className="text-foreground text-sm font-semibold tabular-nums">{rupees(bill.paid)}</p>
                    <p className="text-muted-foreground text-[11px]">
                      {placement.payments.length === 1
                        ? `${METHOD_LABELS[placement.payments[0].method]} · ${asDate(placement.payments[0].paid_at)}`
                        : placement.payments.length > 1
                          ? `${placement.payments.length} receipts · last ${asDate(placement.payments.at(-1)!.paid_at)}`
                          : bill.paid > 0 ? 'Marked paid, no receipt on file' : 'Nothing recorded yet'}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">Still owed</p>
                    <p className={`text-sm font-semibold tabular-nums ${bill.balance > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
                      {rupees(bill.balance)}
                    </p>
                    <p className="text-muted-foreground text-[11px]">{bill.label}</p>
                  </div>
                </div>
              )}

              {/* What the client is paying for versus what they are getting. Over the plan
                  is refused by the API and never reaches here; UNDER it is nobody's error
                  and was invisible -- a five-screen plan running on three is two screens
                  the client has bought and is not receiving. */}
              {placement.plan_max_locations > 0 && (
                <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
                  <MonitorPlay className="text-muted-foreground size-3.5" aria-hidden="true" />
                  <span className="text-muted-foreground">
                    {placement.screens_used} of {placement.plan_max_locations} screens on the{' '}
                    {placement.plan?.name} plan
                  </span>
                  {placement.screens_unused > 0 && (
                    <Badge variant="warning">
                      {placement.screens_unused} paid for, not used
                    </Badge>
                  )}
                </div>
              )}

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
                    {/* The location's own run length, when it was sold one. The API has
                        always returned it; until the type carried it, a booking sold as
                        "airport 50 days, mall 30" looked identical to a uniform one. */}
                    {target.days != null && (
                      <span className="text-muted-foreground text-xs tabular-nums">{target.days}d</span>
                    )}
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

      {/* New booking with visual Plan & Custom package selection */}
      <CreateBookingModal
        open={createOpen}
        onOpenChange={setCreateOpen}
        contentId={contentId}
      />

      {/* Sell more time on an existing booking */}
      <Dialog open={Boolean(extending)} onOpenChange={(open) => !open && setExtending(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Extend booking</DialogTitle>
            <DialogDescription>
              Sell more time on this campaign. It carries on from where the run currently
              finishes, so there is no unpaid gap, and the screens are told straight away.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 pt-2">
            <div className="space-y-2">
              <Label htmlFor="extend-to">Extend until</Label>
              <Input id="extend-to" type="date" value={extendTo} onChange={(e) => setExtendTo(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="extend-price">Additional amount (₹)</Label>
              <Input id="extend-price" type="number" min={0} value={extendPrice} onChange={(e) => setExtendPrice(e.target.value)} placeholder="12500" />
            </div>
            {Boolean(extending?.extensions.length) && (
              <div className="space-y-2">
                <Label>Existing extensions</Label>
                <div className="space-y-1">
                  {extending?.extensions.map((extension) => (
                    <div key={extension.id} className="bg-muted/40 flex items-center justify-between gap-2 rounded-lg px-3 py-2 text-sm">
                      <span>
                        {asDate(extension.extended_from)} → {asDate(extension.extended_to)} · {rupees(extension.additional_price_paise)}
                      </span>
                      <Button
                        size="xs"
                        variant="ghost"
                        className="text-destructive"
                        onClick={() => dropExtension.mutate({ id: extending.id, extensionId: extension.id })}
                        aria-label="Remove this extension"
                      >
                        <X />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setExtending(null)}>Cancel</Button>
            <Button
              onClick={() => extend.mutate()}
              // An end before the current one is a 422 from the server, and a blank price
              // booked a free extension without saying so. A typed 0 is still allowed --
              // goodwill extensions are real, silent ones are not.
              disabled={
                extend.isPending
                || !extendTo
                || !extendPrice.trim()
                || (extending != null
                    && Date.parse(`${extendTo}T23:59:59`)
                       <= Date.parse(extending.effective_ends_at || extending.ends_at))
              }
            >
              Extend
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
              onClick={() => { removeTarget.mutate({ id: splitting!.placement.id, targetId: splitting!.target.id }); setSplitting(null); setExcluded([]) }}
            >
              Remove from the whole group
            </Button>
            <Button disabled={!excluded.length || split.isPending} onClick={() => split.mutate()}>
              {split.isPending ? 'Updating…' : 'Keep the rest'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* --- Change plan ------------------------------------------------------------ */}
      <Dialog open={Boolean(upgrading)} onOpenChange={(open) => { if (!open) setUpgrading(null) }}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Change {upgrading?.advertiser}&apos;s plan</DialogTitle>
            <DialogDescription>
              The booking keeps its history and its report. The difference in price is added
              as an extension, so one client stays one campaign and one invoice.
            </DialogDescription>
          </DialogHeader>

          <div className="max-h-[50vh] space-y-2 overflow-y-auto py-1">
            {/* What the booking is on TODAY, stated before the list of what it could move
                to. The list alone answered it only when the plan was still being sold: a
                campaign on a retired package, or one sold without a package at all, opened
                this dialog with nothing marked current and no way to tell what the client
                had actually bought. */}
            <p className="text-muted-foreground text-sm">
              Currently on{' '}
              <span className="text-foreground font-medium">
                {upgrading?.plan ? upgrading.plan.name : 'no package — a custom price'}
              </span>
              {upgrading && ` · ${rupees(upgrading.total_price_paise ?? upgrading.price_paise)} · runs on ${upgrading.screens_used} screen${upgrading.screens_used === 1 ? '' : 's'}`}
            </p>

            {planOptionsQuery.isPending && <Skeleton className="h-24 w-full" />}
            {planOptionsQuery.isError && (
              <ErrorState
                message="The plans this booking could move to could not be loaded."
                onRetry={() => planOptionsQuery.refetch()}
              />
            )}

            {/* Off the package entirely. Every plan was offered and this was not, so a
                booking put on the wrong plan could be moved between plans but never taken
                off one -- and a client renegotiated onto an agreed figure had nowhere to
                be recorded. */}
            <button
              type="button"
              disabled={!upgrading?.plan}
              onClick={() => setChosenPlan(null)}
              className={`w-full rounded-xl border p-3 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${
                chosenPlan === null ? 'border-primary bg-primary/10 shadow-sm' : 'border-input hover:bg-muted/50'
              }`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium">Custom — no package</span>
                {!upgrading?.plan && <Badge variant="outline">Current</Badge>}
              </div>
              <p className="text-muted-foreground mt-1 text-sm">
                Keeps the price and the run as they are, with no location cap. Edit the
                figure in &ldquo;Edit client &amp; ad details&rdquo;.
              </p>
            </button>

            {planOptionsQuery.isSuccess && !planOptionsQuery.data?.length && (
              <p className="text-muted-foreground text-sm">
                No packages have been set up yet, so custom pricing is the only option.
                Create one under Plans to sell by package.
              </p>
            )}

            {planOptionsQuery.data?.map((option: PlanOption) => {
              const selected = chosenPlan === option.plan.id
              // Retired plans are listed so the current one is always visible, but a plan
              // the tenant has stopped selling must not be sellable again from here.
              const retired = !option.plan.is_active
              return (
                <button
                  key={option.plan.id}
                  type="button"
                  disabled={option.is_current || !option.fits || retired}
                  onClick={() => setChosenPlan(option.plan.id)}
                  className={`w-full rounded-xl border p-3 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${
                    selected ? 'border-primary bg-primary/10 shadow-sm' : 'border-input hover:bg-muted/50'
                  }`}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{option.plan.name}</span>
                    {option.recommended && <Badge variant="success">Recommended</Badge>}
                    {option.is_current && <Badge variant="outline">Current plan</Badge>}
                    {retired && <Badge variant="warning">No longer sold</Badge>}
                    {/* Said plainly rather than just disabled: "why can I not pick this?"
                        is the question a greyed-out row always provokes. */}
                    {!option.fits && (
                      <Badge variant="danger">
                        Covers {option.plan.max_locations}, this booking runs on {upgrading?.screens_used}
                      </Badge>
                    )}
                  </div>
                  <p className="text-muted-foreground mt-1 text-sm">
                    {rupees(option.plan.price_paise)} · {option.plan.duration_days} days · up to{' '}
                    {option.plan.max_locations} screen{option.plan.max_locations === 1 ? '' : 's'}
                    {!option.is_current && option.price_difference_paise > 0 && (
                      <span className="text-foreground"> · +{rupees(option.price_difference_paise)} to move</span>
                    )}
                  </p>
                </button>
              )
            })}
          </div>

          {/* Hidden when moving off a package: there is no plan length to extend by, so
              offering the choice would promise something the change cannot do. */}
          {chosenPlan != null && (
            <>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  className="accent-primary size-4"
                  checked={alsoExtend}
                  onChange={(event) => setAlsoExtend(event.target.checked)}
                />
                Extend the run by the new plan&apos;s length and charge the difference
              </label>
              <p className="text-muted-foreground text-xs">
                Leave this off to correct a booking that is on the wrong plan without selling
                any extra time. Anything charged is added to what the client owes.
              </p>
            </>
          )}

          <DialogFooter showCloseButton>
            <Button
              disabled={chosenPlan === undefined || upgrade.isPending}
              onClick={() => upgrade.mutate()}
            >
              {upgrade.isPending ? 'Changing…' : chosenPlan === null ? 'Move off the package' : 'Change plan'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* --- Record payment ---------------------------------------------------------
          A ledger: saving ADDS a receipt. It used to overwrite the single settlement row,
          so typing "5000" for a second ₹5,000 instalment filed the client as having paid
          ₹5,000 of ₹10,000 and took the first receipt's date, method and reference with
          it. The box is now this instalment, every receipt already taken is listed, and
          the balance after saving is shown before anything is written. */}
      <Dialog open={Boolean(paying)} onOpenChange={(open) => { if (!open) setPaying(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Payment from {paying?.advertiser}</DialogTitle>
            <DialogDescription>
              What the client has handed over this time. Each payment is kept as its own
              receipt, so a deposit and a balance both stay on the record.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            {paying && (() => {
              const bill = money(paying)
              const entered = Math.round(Number(payAmount || 0) * 100)
              // Against the BALANCE, not the contract: this instalment lands on top of
              // what has already been received rather than replacing it.
              const after = bill.balance - entered
              return (
                <div className="bg-muted/40 ring-hairline space-y-2 rounded-xl p-3 text-sm ring-1">
                  <div className="flex justify-between gap-3">
                    <span className="text-muted-foreground">Contract value</span>
                    <span className="text-foreground font-semibold tabular-nums">{rupees(bill.total)}</span>
                  </div>
                  <div className="flex justify-between gap-3">
                    <span className="text-muted-foreground">Recorded so far</span>
                    <span className="text-foreground font-semibold tabular-nums">{rupees(bill.paid)}</span>
                  </div>
                  <div className="border-hairline flex justify-between gap-3 border-t pt-2">
                    <span className="text-muted-foreground">Balance after saving</span>
                    <span className={`font-semibold tabular-nums ${after > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
                      {after > 0 ? rupees(after) : 'Nothing owing'}
                    </span>
                  </div>
                  {entered > bill.balance && (
                    <p className="text-amber-600 dark:text-amber-400">
                      That is {rupees(entered - bill.balance)} more than is still owed. Saved
                      as an overpayment.
                    </p>
                  )}
                </div>
              )
            })()}
            <div className="space-y-1.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Label htmlFor="pay-amount">Amount received now (₹)</Label>
                {paying && money(paying).balance > 0 && (
                  // One click for the case the box is most often filled by hand for: the
                  // client has now settled the lot.
                  <Button
                    size="xs"
                    variant="ghost"
                    onClick={() => setPayAmount(String(money(paying).balance / 100))}
                  >
                    Settles the balance
                  </Button>
                )}
              </div>
              <Input id="pay-amount" type="number" min={0} value={payAmount}
                     onChange={(event) => setPayAmount(event.target.value)} autoFocus />
              <p className="text-muted-foreground text-xs">
                Part payments are fine — this is added to what has already been received,
                and the booking stays part paid until the two together cover the contract.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="pay-method">Method</Label>
                <select
                  id="pay-method"
                  className="border-input bg-background h-10 w-full rounded-lg border px-3 text-sm"
                  value={payMethod}
                  onChange={(event) => setPayMethod(event.target.value as PaymentMethod)}
                >
                  <option value="cash">Cash</option>
                  <option value="upi">UPI</option>
                  <option value="bank_transfer">Bank transfer</option>
                  <option value="cheque">Cheque</option>
                  <option value="card">Card</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="pay-date">Received on</Label>
                <Input id="pay-date" type="date" value={payDate}
                       onChange={(event) => setPayDate(event.target.value)} />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="pay-ref">Reference</Label>
              <Input id="pay-ref" value={payReference} placeholder="UTR, cheque number, transaction id"
                     onChange={(event) => setPayReference(event.target.value)} />
            </div>
            {/* The receipts already taken, in the order the money arrived. An operator
                asking "did we already enter that transfer?" was answering it from a single
                prefilled box, which is exactly how the same payment got typed twice. */}
            {paying && paying.payments.length > 0 && (
              <div className="space-y-1.5">
                <Label>Already received</Label>
                <ul className="border-hairline divide-hairline divide-y rounded-xl border">
                  {paying.payments.map((receipt) => (
                    <li key={receipt.id} className="flex items-center justify-between gap-3 p-2.5 text-sm">
                      <div className="min-w-0">
                        <p className="text-foreground font-medium tabular-nums">
                          {rupees(receipt.amount_paise)}
                          <span className="text-muted-foreground font-normal">
                            {' · '}{METHOD_LABELS[receipt.method]}{' · '}{asDate(receipt.paid_at)}
                          </span>
                        </p>
                        {(receipt.reference || receipt.recorded_by) && (
                          <p className="text-muted-foreground truncate text-xs">
                            {receipt.reference && `Ref ${receipt.reference}`}
                            {receipt.reference && receipt.recorded_by && ' · '}
                            {receipt.recorded_by && `recorded by ${receipt.recorded_by}`}
                          </p>
                        )}
                      </div>
                      {/* A wrong amount is corrected by removing the receipt and entering
                          the right one, so the ledger reads as what happened. */}
                      <Button
                        size="xs"
                        variant="ghost"
                        className="text-destructive shrink-0"
                        disabled={deletePayment.isPending}
                        onClick={() => deletePayment.mutate(receipt.id)}
                      >
                        Remove
                      </Button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <DialogFooter showCloseButton>
            {/* Everything off at once. Also the only way to clear a booking flagged paid
                before payments were recorded: it has no receipt to remove. */}
            {(paying?.payments.length || paying?.is_paid) ? (
              <Button variant="ghost" className="text-destructive" disabled={clearPayment.isPending}
                      onClick={() => clearPayment.mutate()}>
                Clear all
              </Button>
            ) : null}
            {/* A zero is not a payment, it is a clearing -- and there is a button for
                that beside this one. Saving one wrote a receipt for nothing and left the
                booking looking settled-with-nothing-received. */}
            <Button
              disabled={savePayment.isPending || !(Number(payAmount) > 0)}
              onClick={() => savePayment.mutate()}
            >
              {savePayment.isPending ? 'Saving…' : 'Save payment'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* --- Delete confirmation ---------------------------------------------------- */}
      <Dialog open={Boolean(deleting)} onOpenChange={(open) => { if (!open) setDeleting(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete {deleting?.advertiser}&apos;s booking?</DialogTitle>
            <DialogDescription>
              This removes the sale and pulls the advert off{' '}
              {deleting?.targets.length ?? 0} place{deleting?.targets.length === 1 ? '' : 's'} straight
              away. The playback history stays, but the booking and its report do not.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter showCloseButton>
            <Button
              variant="destructive"
              disabled={remove.isPending}
              onClick={() => { remove.mutate(deleting!.id); setDeleting(null) }}
            >
              {remove.isPending ? 'Deleting…' : 'Delete booking'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <EmailReportModal
        placement={emailPlacement}
        open={Boolean(emailPlacement)}
        onOpenChange={(open) => {
          if (!open) setEmailPlacement(null)
        }}
      />
    </div>
  )
}
