'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CalendarRange, FileDown, IndianRupee, Mail, Receipt, Search } from 'lucide-react'
import { toast } from 'sonner'
import { EmptyState } from '@/components/dashboard/empty-state'
import { ErrorState } from '@/components/dashboard/error-state'
import { PageHeader } from '@/components/dashboard/page-header'
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
import type { PaymentMethod, Placement } from '@/lib/types'
import { bookingState, rupees } from '@/lib/format'

const asDate = (iso: string) => new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })

const METHOD_LABELS: Record<PaymentMethod, string> = {
  cash: 'Cash', upi: 'UPI', bank_transfer: 'Bank transfer',
  cheque: 'Cheque', card: 'Card', other: 'Other',
}

const owed = (placement: Placement) => placement.total_price_paise ?? placement.price_paise

type Filter = 'all' | 'unpaid' | 'paid'

/**
 * What every client owes this workspace, and what they have paid.
 *
 * Deliberately NOT /dashboard/billing, which is this workspace's own subscription to
 * OLRAC. These are two different sets of books that used to bleed into each other: the
 * playback report carried the price and the paid pill, and the campaigns page totted up
 * revenue on a page called "Playback report". Delivery evidence lives there; money lives
 * here.
 */
export default function InvoicesPage() {
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)
  const canEdit = canEditTenantContent(user)

  const placementsQuery = useQuery({ queryKey: ['all-placements'], queryFn: api.getAllPlacements })
  const placements = useMemo(() => placementsQuery.data || [], [placementsQuery.data])

  const [filter, setFilter] = useState<Filter>('all')
  const [search, setSearch] = useState('')

  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase()
    return placements.filter((placement) => {
      // On the balance, not the flag: a part-paid booking still owes money and belongs
      // in Unpaid, which is the list a tenant works through when chasing.
      const stillOwed = Math.max(0, owed(placement) - (placement.payment?.amount_paise ?? 0))
      if (filter === 'paid' && stillOwed > 0) return false
      if (filter === 'unpaid' && stillOwed === 0) return false
      if (!needle) return true
      return [placement.advertiser, placement.client?.name, placement.client?.client_code, placement.creative_name]
        .some((field) => field?.toLowerCase().includes(needle))
    })
  }, [placements, filter, search])

  // Outstanding counts what has NOT been settled, not what has been billed. A tenant
  // chasing money wants the second number, and the revenue tile on the campaigns page was
  // showing them the first.
  //
  // Per booking it is total MINUS received, not a test of the is_paid flag. Reading the
  // flag made a part payment settle the whole booking: recording ₹5,000 against a ₹12,000
  // campaign showed ₹0 outstanding in the tile while the row beside it said ₹7,000 was
  // still owed.
  const balance = (p: Placement) => Math.max(0, owed(p) - (p.payment?.amount_paise ?? 0))
  const outstanding = placements.reduce((sum, p) => sum + balance(p), 0)
  const collected = placements.reduce((sum, p) => sum + (p.payment?.amount_paise ?? 0), 0)
  const awaiting = placements.filter((p) => balance(p) > 0).length

  const [paying, setPaying] = useState<Placement | null>(null)
  const [payAmount, setPayAmount] = useState('')
  const [payMethod, setPayMethod] = useState<PaymentMethod>('upi')
  const [payReference, setPayReference] = useState('')
  const [payDate, setPayDate] = useState('')
  const [busy, setBusy] = useState<number | null>(null)

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['all-placements'] })
  const fail = (error: Error) => toast.error(error.message)

  const openPayment = (placement: Placement) => {
    setPaying(placement)
    const existing = placement.payment
    setPayAmount(String(((existing?.amount_paise ?? owed(placement)) || 0) / 100))
    setPayMethod(existing?.method ?? 'upi')
    setPayReference(existing?.reference ?? '')
    setPayDate((existing?.paid_at ?? new Date().toISOString()).slice(0, 10))
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
    onSuccess: () => { refresh(); toast.success('Payment cleared; the booking is unpaid again'); setPaying(null) },
    onError: fail,
  })

  const download = async (placement: Placement) => {
    setBusy(placement.id)
    try {
      await api.downloadInvoice(placement.id)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'The invoice could not be generated.')
    } finally {
      setBusy(null)
    }
  }

  const email = async (placement: Placement) => {
    setBusy(placement.id)
    try {
      const sent = await api.emailBookingReport(placement.id, 'invoice')
      toast.success(`Invoice emailed to ${sent.to}`)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'The invoice could not be sent.')
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Client billing"
        title="Invoices"
        description="What each client owes for their airtime, and what they have paid. Your own OLRAC subscription is under Billing."
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="ring-hairline bg-card rounded-2xl p-5 shadow-sm ring-1">
          <p className="text-muted-foreground text-xs font-semibold uppercase">Outstanding</p>
          <p className="mt-1 font-mono text-2xl font-bold tabular-nums">{rupees(outstanding)}</p>
          <p className="text-muted-foreground text-xs">Billed and not yet settled</p>
        </div>
        <div className="ring-hairline bg-card rounded-2xl p-5 shadow-sm ring-1">
          <p className="text-muted-foreground text-xs font-semibold uppercase">Collected</p>
          <p className="mt-1 font-mono text-2xl font-bold tabular-nums">{rupees(collected)}</p>
          <p className="text-muted-foreground text-xs">Recorded against a payment</p>
        </div>
        <div className="ring-hairline bg-card rounded-2xl p-5 shadow-sm ring-1">
          <p className="text-muted-foreground text-xs font-semibold uppercase">Bookings</p>
          <p className="mt-1 font-mono text-2xl font-bold tabular-nums">{placements.length}</p>
          <p className="text-muted-foreground text-xs">
            {awaiting} awaiting payment
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="bg-muted flex gap-1 rounded-xl p-1">
          {(['all', 'unpaid', 'paid'] as Filter[]).map((option) => (
            <Button
              key={option}
              size="sm"
              variant={filter === option ? 'default' : 'ghost'}
              className="capitalize"
              onClick={() => setFilter(option)}
            >
              {option}
            </Button>
          ))}
        </div>
        <div className="relative min-w-56 flex-1">
          <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2" aria-hidden="true" />
          <Input
            className="pl-9"
            placeholder="Search client, code or creative"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            aria-label="Search invoices"
          />
        </div>
      </div>

      {placementsQuery.isPending && <Skeleton className="h-64 w-full" />}
      {placementsQuery.isError && (
        <ErrorState message="The invoices could not be loaded." onRetry={() => placementsQuery.refetch()} />
      )}

      {placementsQuery.isSuccess && !visible.length && (
        <EmptyState
          icon={Receipt}
          title={placements.length ? 'Nothing matches that' : 'No bookings sold yet'}
          description={
            placements.length
              ? 'Try a different search, or clear the filter.'
              : 'Sell an advert to a client and its invoice will appear here.'
          }
        />
      )}

      {visible.map((placement) => {
        const state = bookingState(placement)
        const total = owed(placement)
        const received = placement.payment?.amount_paise ?? 0
        const short = placement.payment ? total - received : 0
        return (
          <Card key={placement.id} className="ring-hairline bg-card border-0 ring-1">
            <CardContent className="flex flex-wrap items-start justify-between gap-4 p-5">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-foreground font-semibold">{placement.advertiser}</h3>
                  <Badge variant={state.tone}>{state.label}</Badge>
                  {placement.client && <Badge variant="outline">{placement.client.client_code}</Badge>}
                  {/* Part paid is its own state. "Paid" over an outstanding balance is the
                      kind of contradiction a client rings up about. */}
                  {placement.is_paid && short > 0 ? (
                    <Badge variant="warning">Part paid · {rupees(short)} outstanding</Badge>
                  ) : (
                    <Badge variant={placement.is_paid ? 'success' : 'warning'}>
                      {placement.is_paid ? 'Paid' : 'Unpaid'}
                    </Badge>
                  )}
                  {placement.payment && (
                    <Badge variant="outline">{METHOD_LABELS[placement.payment.method]}</Badge>
                  )}
                </div>
                <p className="text-muted-foreground mt-1 flex flex-wrap items-center gap-1.5 text-sm">
                  <CalendarRange className="size-3.5" aria-hidden="true" />
                  {asDate(placement.starts_at)} → {asDate(placement.effective_ends_at || placement.ends_at)}
                  {placement.plan && <span>· {placement.plan.name}</span>}
                  {placement.creative_name && (
                    <Link href={`/dashboard/content/${placement.content_id}`} className="text-primary hover:underline">
                      · {placement.creative_name}
                    </Link>
                  )}
                </p>
                {placement.payment?.reference && (
                  <p className="text-muted-foreground mt-1 text-xs">
                    Ref {placement.payment.reference} · received {asDate(placement.payment.paid_at)}
                    {placement.payment.recorded_by && ` · recorded by ${placement.payment.recorded_by}`}
                  </p>
                )}
              </div>

              <div className="flex shrink-0 items-center gap-3">
                <p className="font-mono text-lg font-semibold tabular-nums">{rupees(total)}</p>
                <Button size="sm" variant="outline" disabled={busy === placement.id} onClick={() => download(placement)}>
                  <FileDown data-icon="inline-start" /> Invoice
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={busy === placement.id || !placement.client?.email}
                  title={placement.client?.email ? 'Email this invoice to the client' : 'This client has no email address on file'}
                  onClick={() => email(placement)}
                >
                  <Mail data-icon="inline-start" /> Email
                </Button>
                {canEdit && (
                  <Button
                    size="sm"
                    variant={placement.is_paid ? 'outline' : 'default'}
                    onClick={() => openPayment(placement)}
                  >
                    <IndianRupee data-icon="inline-start" />
                    {placement.is_paid ? 'Payment' : 'Record payment'}
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        )
      })}

      <Dialog open={Boolean(paying)} onOpenChange={(open) => { if (!open) setPaying(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Payment from {paying?.advertiser}</DialogTitle>
            <DialogDescription>
              Recording this is what marks the booking paid. Owed in total:{' '}
              {rupees(paying ? owed(paying) : 0)}.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="inv-amount">Amount received (₹)</Label>
              <Input id="inv-amount" type="number" min={0} value={payAmount}
                     onChange={(event) => setPayAmount(event.target.value)} autoFocus />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="inv-method">Method</Label>
                <select
                  id="inv-method"
                  className="border-input bg-background h-10 w-full rounded-lg border px-3 text-sm"
                  value={payMethod}
                  onChange={(event) => setPayMethod(event.target.value as PaymentMethod)}
                >
                  {(Object.keys(METHOD_LABELS) as PaymentMethod[]).map((method) => (
                    <option key={method} value={method}>{METHOD_LABELS[method]}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="inv-date">Received on</Label>
                <Input id="inv-date" type="date" value={payDate}
                       onChange={(event) => setPayDate(event.target.value)} />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="inv-ref">Reference</Label>
              <Input id="inv-ref" value={payReference} placeholder="UTR, cheque number, transaction id"
                     onChange={(event) => setPayReference(event.target.value)} />
            </div>
          </div>

          <DialogFooter showCloseButton>
            {paying?.payment && (
              <Button variant="ghost" className="text-destructive" disabled={clearPayment.isPending}
                      onClick={() => clearPayment.mutate()}>
                Clear payment
              </Button>
            )}
            <Button disabled={savePayment.isPending} onClick={() => savePayment.mutate()}>
              {savePayment.isPending ? 'Saving…' : 'Record payment'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
