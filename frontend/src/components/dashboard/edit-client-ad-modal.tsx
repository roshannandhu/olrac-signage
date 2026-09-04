'use client'

import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Building2, Check, IndianRupee, Mail, Phone, Tag, X } from 'lucide-react'
import { api } from '@/lib/api'
import { rupees } from '@/lib/format'
import { invalidateBookingViews } from '@/lib/query-keys'
import type { Client, ContentItem, Screen, TenantPlan } from '@/lib/types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface EditClientAdModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  contentItem: ContentItem | null
  /**
   * Screens to tick by default for an advert that has none yet.
   *
   * Passed by the playlist builder, where the "+" sits beside a loop the operator is
   * already looking at. Without it the modal opened with nothing selected, the operator
   * booked the advert, and it went to no screen at all -- the loop was unchanged and
   * nothing reached the TV, which read as "adding content does nothing".
   *
   * Only a default. An advert that already has screens keeps them, so re-opening the
   * modal from a different playlist cannot quietly re-target a live booking.
   */
  defaultScreenIds?: number[]
}

export function EditClientAdModal({ open, onOpenChange, contentItem, defaultScreenIds }: EditClientAdModalProps) {
  const queryClient = useQueryClient()

  const [name, setName] = useState('')
  const [clientName, setClientName] = useState('')
  const [clientEmail, setClientEmail] = useState('')
  const [clientPhone, setClientPhone] = useState('')
  const [planId, setPlanId] = useState<number | null>(null)
  // Rupees as typed, converted to paise on the wire. A string rather than a number so the
  // box can be EMPTY -- which is not the same as zero, and zero is a real price a booking
  // can legitimately carry (a make-good, a bonus run).
  const [price, setPrice] = useState('')
  const [selectedScreenIds, setSelectedScreenIds] = useState<number[]>([])
  const [notes, setNotes] = useState('')
  // Per-location run lengths, keyed by screen id.
  //
  // Off by default: most sales are one length everywhere, and the plan already says what
  // that is. Turned on, a client can buy 30 days in a mall, 10 in a shop and 50 at an
  // airport as ONE booking -- previously only expressible as three, which meant three
  // invoice lines and three extensions for one deal.
  const [customDurations, setCustomDurations] = useState(false)
  const [screenDays, setScreenDays] = useState<Record<number, number>>({})
  const [showClientSuggestions, setShowClientSuggestions] = useState(false)

  // Load available clients for auto-complete
  const { data: clients = [] } = useQuery<Client[]>({
    queryKey: ['clients'],
    queryFn: () => api.getClients(),
    enabled: open,
  })

  // Load tenant pricing plans
  const { data: plans = [] } = useQuery<TenantPlan[]>({
    queryKey: ['tenant-plans'],
    queryFn: () => api.getTenantPlans(),
    enabled: open,
  })

  // Load active screens
  const { data: screens = [] } = useQuery<Screen[]>({
    queryKey: ['screens'],
    queryFn: () => api.getScreens(),
    enabled: open,
  })

  // Pre-fill fields when modal opens with contentItem
  useEffect(() => {
    if (contentItem && open) {
      setName(contentItem.name || '')
      setClientName(contentItem.client_name || '')
      setClientEmail(contentItem.client_email || '')
      setClientPhone(contentItem.client_phone || '')
      setPlanId(contentItem.plan_id || null)
      // What this booking is actually billed, which for a custom sale is the only place
      // the figure exists. Blank on an advert with no booking yet, so picking a plan can
      // fill it without overwriting anything.
      setPrice(
        contentItem.placement_price_paise != null
          ? String(contentItem.placement_price_paise / 100)
          : '',
      )
      // Existing targets win; the default only fills an empty selection.
      const existing = contentItem.screen_ids || []
      setSelectedScreenIds(existing.length ? existing : (defaultScreenIds || []))
      const soldDays = contentItem.screen_days || {}
      setScreenDays(soldDays)
      // Opened already on, so an operator editing a bespoke booking sees the lengths it
      // was actually sold rather than a collapsed panel implying one uniform run.
      setCustomDurations(Object.keys(soldDays).length > 0)
      setNotes(contentItem.placement_notes || '')
    }
    // Deliberately narrower than the values used. `contentItem` is a fresh object after
    // every ['content'] refetch and `defaultScreenIds` a fresh array after every ['screens']
    // one, so depending on them by identity re-seeded this form -- wiping whatever the
    // operator was halfway through typing -- any time something else invalidated a query.
    // Seeding is keyed on which asset is open, which is what actually decides it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, contentItem?.id, (defaultScreenIds || []).join(',')])

  // Selected plan metadata
  const selectedPlan = useMemo(() => {
    return plans.find((p) => p.id === planId) || null
  }, [plans, planId])

  // Null means "no cap", which is not the same as "capped at however many screens exist".
  // A booking on a RETIRED plan also lands here, because getTenantPlans returns active
  // plans only -- so the badge must not imply an allowance that was never sold.
  const maxAllowedScreens = selectedPlan && selectedPlan.max_locations > 0
    ? selectedPlan.max_locations
    : null

  // Filter client suggestions
  const filteredClients = useMemo(() => {
    if (!clientName.trim()) return clients.slice(0, 5)
    return clients.filter((c) => c.name.toLowerCase().includes(clientName.toLowerCase())).slice(0, 5)
  }, [clients, clientName])

  // Mutation to update client and ad details
  const updateMutation = useMutation({
    mutationFn: async () => {
      if (!contentItem) return
      return api.updateContentClientAd(contentItem.id, {
        name: name.trim() || undefined,
        client_name: clientName.trim(),
        client_email: clientEmail.trim() || undefined,
        client_phone: clientPhone.trim() || undefined,
        plan_id: planId,
        // Only when a figure was typed. Sending null leaves the agreed price alone, so an
        // edit to a phone number cannot restate what a client owes.
        price_paise: price.trim() === '' ? undefined : Math.round(Number(price) * 100),
        screen_ids: selectedScreenIds,
    // Only the selected screens, and only when the operator asked for per-location
    // lengths. Turning the toggle off is a deliberate "make this one uniform window",
    // sent as its own flag -- an empty map would be indistinguishable from a client that
    // does not know the field exists, and the API refuses to destroy a paid schedule on
    // that basis.
    screen_days: customDurations
      ? Object.fromEntries(selectedScreenIds.filter((id) => screenDays[id]).map((id) => [id, screenDays[id]]))
      : undefined,
    clear_screen_days: !customDurations,
        notes: notes.trim() || undefined,
      })
    },
    onSuccess: () => {
      toast.success('Ad and client details updated successfully')
      invalidateBookingViews(queryClient)
      onOpenChange(false)
    },
    onError: (err: Error) => {
      toast.error(err.message || 'Failed to update client & ad details')
    },
  })

  const toggleScreen = (screenId: number) => {
    setSelectedScreenIds((prev) => {
      if (prev.includes(screenId)) {
        return prev.filter((id) => id !== screenId)
      }
      if (maxAllowedScreens !== null && prev.length >= maxAllowedScreens) {
        toast.error(`Your plan (${selectedPlan?.name || 'Selected'}) is capped at ${maxAllowedScreens} screen(s).`)
        return prev
      }
      return [...prev, screenId]
    })
  }

  /** Close the suggestion list when focus leaves the name field and the list together. */
  const closeSuggestionsOnBlur = (event: React.FocusEvent<HTMLDivElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
      setShowClientSuggestions(false)
    }
  }

  const handleSelectClient = (c: Client) => {
    setClientName(c.name)
    if (c.email) setClientEmail(c.email)
    if (c.phone) setClientPhone(c.phone)
    setShowClientSuggestions(false)
  }

  if (!contentItem) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto p-6 sm:p-7">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="size-9 rounded-xl bg-primary/10 text-primary grid place-items-center">
              <Building2 className="size-5" />
            </div>
            <div>
              <DialogTitle className="text-xl">Edit Client & Ad Details</DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground mt-0.5">
                Update advertiser information, commercial package, and screen allocation for this ad.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-6 py-2">
          {/* Ad Title */}
          <div className="space-y-1.5">
            <Label htmlFor="ad-name" className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Ad / Creative Title
            </Label>
            <div className="relative">
              <Tag className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
              <Input
                id="ad-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Moolans Grand Opening Offer"
                className="pl-9 text-sm"
              />
            </div>
          </div>

          {/* Section: Client & Advertiser */}
          <div className="rounded-2xl border border-primary/20 bg-primary/[0.02] p-4 sm:p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Building2 className="size-4 text-primary" />
                <span className="text-xs font-bold uppercase tracking-wider text-primary">Client & Advertiser (Required)</span>
              </div>
              <Badge variant="outline" className="text-[10px] font-medium border-primary/30 text-primary">
                1:1 Ad Booking
              </Badge>
            </div>

            <div className="space-y-3">
              {/* Client Name with Auto-Complete */}
              <div className="space-y-1.5 relative" onBlur={closeSuggestionsOnBlur}>
                <Label htmlFor="client-name" className="text-xs font-medium">
                  Client / Brand Name <span className="text-rose-500">*</span>
                </Label>
                <div className="relative">
                  <Input
                    id="client-name"
                    value={clientName}
                    onChange={(e) => {
                      setClientName(e.target.value)
                      setShowClientSuggestions(true)
                    }}
                    onFocus={() => setShowClientSuggestions(true)}
                    placeholder="Type or select client name..."
                    className="text-sm bg-background"
                  />
                  {clientName && (
                    <button
                      type="button"
                      onClick={() => {
                        setClientName('')
                        setShowClientSuggestions(false)
                      }}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      <X className="size-4" />
                    </button>
                  )}
                </div>

                {/* Dropdown Suggestions */}
                {showClientSuggestions && filteredClients.length > 0 && (
                  <div className="absolute z-50 left-0 right-0 top-full mt-1 rounded-xl border border-border bg-popover shadow-xl overflow-hidden divide-y divide-border/40">
                    <div className="px-3 py-1.5 bg-muted/40 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                      Existing Clients
                    </div>
                    {filteredClients.map((c) => (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => handleSelectClient(c)}
                        className="w-full text-left px-3 py-2 text-xs hover:bg-primary/10 flex items-center justify-between transition-colors"
                      >
                        <span className="font-semibold text-foreground">{c.name}</span>
                        <span className="text-[11px] text-muted-foreground">{c.email || c.phone || c.client_code}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Email & Phone */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="client-email" className="text-xs font-medium">
                    Client Email
                  </Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
                    <Input
                      id="client-email"
                      type="email"
                      value={clientEmail}
                      onChange={(e) => setClientEmail(e.target.value)}
                      placeholder="client@brand.com"
                      className="pl-9 text-xs bg-background"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="client-phone" className="text-xs font-medium">
                    Client Phone
                  </Label>
                  <div className="relative">
                    <Phone className="absolute left-3 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
                    <Input
                      id="client-phone"
                      value={clientPhone}
                      onChange={(e) => setClientPhone(e.target.value)}
                      placeholder="+91 98765 43210"
                      className="pl-9 text-xs bg-background"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Section: Pricing Plan */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Pricing Plan & Package
              </Label>
              {selectedPlan && (
                <Badge variant="outline" className="text-[11px] font-semibold text-emerald-500 border-emerald-500/30">
                  {rupees(selectedPlan.price_paise)} • {selectedPlan.duration_days} Days
                </Badge>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {/* Not every client buys a package. Without this tile a plan could be picked
                  but never un-picked, so a booking sold on an agreed figure had no way to
                  be recorded as one -- and a new advert left on no plan was created at zero
                  with no field anywhere to say otherwise. */}
              <button
                type="button"
                onClick={() => setPlanId(null)}
                className={`text-left p-3 rounded-xl border transition-all ${
                  planId === null
                    ? 'border-primary bg-primary/10 shadow-sm'
                    : 'border-border/60 hover:border-border hover:bg-muted/30'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-xs text-foreground">Custom — no package</span>
                  <span className="text-xs font-bold text-primary">You set the price</span>
                </div>
                <div className="mt-1 text-[11px] text-muted-foreground">
                  No location cap · set the run length per screen below
                </div>
              </button>
              {plans.map((p) => {
                const isSelected = planId === p.id
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => {
                      setPlanId(p.id)
                      // Fills the price only when nothing is there. Overwriting would
                      // restate a figure already agreed with the client -- the same
                      // silent rebill the API refuses to do when a plan is repriced.
                      setPrice((current) => (current.trim() === '' ? String(p.price_paise / 100) : current))
                    }}
                    className={`text-left p-3 rounded-xl border transition-all ${
                      isSelected
                        ? 'border-primary bg-primary/10 shadow-sm'
                        : 'border-border/60 hover:border-border hover:bg-muted/30'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-xs text-foreground">{p.name}</span>
                      <span className="text-xs font-bold text-primary">{rupees(p.price_paise)}</span>
                    </div>
                    <div className="flex items-center gap-2 mt-1 text-[11px] text-muted-foreground">
                      <span>{p.duration_days} days</span>
                      <span>•</span>
                      <span>Max {p.max_locations} screen{p.max_locations > 1 ? 's' : ''}</span>
                    </div>
                  </button>
                )
              })}
            </div>

            {/* The figure the client is actually billed, whichever tile is selected. A plan
                fills it in as a starting point; it stays editable because a negotiated
                price and a discount are both ordinary, and neither was expressible. */}
            <div className="space-y-1.5 pt-1">
              <Label htmlFor="ad-price" className="text-xs font-medium">
                Contract price (₹) {planId === null && <span className="text-rose-500">*</span>}
              </Label>
              <div className="relative">
                <IndianRupee className="absolute left-3 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
                <Input
                  id="ad-price"
                  type="number"
                  min={0}
                  step="0.01"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  placeholder={selectedPlan ? String(selectedPlan.price_paise / 100) : '25000'}
                  className="pl-9 text-sm bg-background"
                />
              </div>
              <p className="text-[11px] text-muted-foreground">
                {planId === null
                  ? 'No package selected, so this is the whole of what the client is billed.'
                  : `Pre-filled from ${selectedPlan?.name || 'the plan'}. Change it to bill something else.`}
              </p>
            </div>
          </div>

          {/* Section: Screen Allocation */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Assigned Screens
              </Label>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setCustomDurations((on) => !on)}
                  aria-pressed={customDurations}
                  className={`rounded-lg border px-2 py-1 text-[11px] font-semibold transition-colors ${
                    customDurations
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border/60 text-muted-foreground hover:bg-muted/40'
                  }`}
                >
                  Custom days per location
                </button>
                <Badge
                  variant={maxAllowedScreens !== null && selectedScreenIds.length > maxAllowedScreens ? 'danger' : 'outline'}
                  className="text-[11px] font-semibold"
                >
                  {maxAllowedScreens !== null
                    ? `${selectedScreenIds.length} of ${maxAllowedScreens} screens assigned`
                    : `${selectedScreenIds.length} screen${selectedScreenIds.length === 1 ? '' : 's'} assigned`}
                </Badge>
              </div>
            </div>

            {screens.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border/70 p-4 text-center text-xs text-muted-foreground">
                No active screens available in this workspace.
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-48 overflow-y-auto pr-1">
                {screens.map((screen) => {
                  const isChecked = selectedScreenIds.includes(screen.id)
                  return (
                    <button
                      key={screen.id}
                      type="button"
                      onClick={() => toggleScreen(screen.id)}
                      className={`flex items-center gap-2.5 p-2.5 rounded-xl border text-left transition-all ${
                        isChecked
                          ? 'border-primary/80 bg-primary/10 text-foreground'
                          : 'border-border/50 hover:bg-muted/40 text-muted-foreground'
                      }`}
                    >
                      <div
                        className={`size-4 rounded border grid place-items-center shrink-0 transition-colors ${
                          isChecked ? 'border-primary bg-primary text-primary-foreground' : 'border-muted-foreground/40'
                        }`}
                      >
                        {isChecked && <Check className="size-3" />}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-medium truncate text-foreground">{screen.name || `Screen #${screen.id}`}</p>
                        <p className="text-[10px] text-muted-foreground truncate">{screen.location || 'Default Location'}</p>
                      </div>
                      {/* Rendered inside the row but OUTSIDE the click target's effect:
                          stopPropagation, or typing a duration would untick the screen. */}
                      {customDurations && isChecked && (
                        <span
                          className="flex shrink-0 items-center gap-1"
                          onClick={(event) => event.stopPropagation()}
                        >
                          <input
                            type="number"
                            min={1}
                            max={3650}
                            aria-label={`Days for ${screen.name || `Screen #${screen.id}`}`}
                            value={screenDays[screen.id] ?? ''}
                            placeholder={String(selectedPlan?.duration_days ?? '')}
                            onChange={(event) => {
                              const value = Number(event.target.value)
                              setScreenDays((current) => {
                                const next = { ...current }
                                // Cleared means "follow the booking", so the key is removed
                                // rather than stored as 0 -- which would be a zero-day run.
                                if (!value || value < 1) delete next[screen.id]
                                else next[screen.id] = value
                                return next
                              })
                            }}
                            className="w-14 rounded-lg border border-border/60 bg-background px-1.5 py-1 text-center text-[11px] text-foreground outline-none focus:border-primary"
                          />
                          <span className="text-[10px] text-muted-foreground">days</span>
                        </span>
                      )}
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          {/* Notes */}
          <div className="space-y-1.5">
            <Label htmlFor="notes" className="text-xs font-medium text-muted-foreground">
              Campaign Notes / Reference
            </Label>
            <Input
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Special festive discount banner"
              className="text-xs"
            />
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0 mt-4">
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          {/* Save is blocked when over the cap, not merely coloured red. Switching to a
              smaller plan left the earlier selection in place, so the badge turned danger
              and Save stayed enabled -- and the API then refused the whole edit with a 409
              that read as a failure rather than as the choice it was. */}
          <Button
            type="button"
            disabled={
              !clientName.trim()
              || updateMutation.isPending
              || (maxAllowedScreens !== null && selectedScreenIds.length > maxAllowedScreens)
              || (customDurations && selectedScreenIds.some((id) => !screenDays[id]))
              // No package AND no figure is exactly how a sale ended up recorded as free.
              || (planId === null && price.trim() === '')
            }
            onClick={() => updateMutation.mutate()}
            className="font-semibold shadow-md"
          >
            {updateMutation.isPending ? 'Saving Changes...' : 'Save Details'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
