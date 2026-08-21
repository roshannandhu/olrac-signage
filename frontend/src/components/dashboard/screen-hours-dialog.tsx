'use client'

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { api } from '@/lib/api'
import { WEEKDAYS, type OperatingMode, type Screen } from '@/lib/types'

const ALL_DAY: [string, string] = ['00:00', '23:59']

const MODES: { value: OperatingMode; label: string }[] = [
  { value: 'always', label: 'is always on' },
  { value: 'hours', label: 'is in use during these times:' },
  { value: 'never', label: 'is switched off' },
]

type Windows = Record<string, [string, string]>

const withDefaults = (saved: Windows | null | undefined): Windows =>
  Object.fromEntries(WEEKDAYS.map(({ key }) => [key, saved?.[key] ?? ALL_DAY])) as Windows

export function ScreenHoursDialog({
  screen,
  open,
  onOpenChange,
}: {
  screen: Screen
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<OperatingMode>(screen.operating_mode || 'always')
  const [windows, setWindows] = useState<Windows>(withDefaults(screen.operating_hours))

  const setDay = (day: string, index: 0 | 1, value: string) =>
    setWindows((current) => {
      const next: [string, string] = [...current[day]] as [string, string]
      next[index] = value
      return { ...current, [day]: next }
    })

  // A day whose end is at or before its start would never play; catching it here keeps
  // the screen from going dark on a typo.
  const invalid = mode === 'hours'
    ? WEEKDAYS.filter(({ key }) => windows[key][1] <= windows[key][0]).map(({ label }) => label)
    : []

  const save = useMutation({
    mutationFn: () => api.patchScreen(screen.id, {
      operating_mode: mode,
      // Windows are kept even when the mode is not "hours", so switching back does not
      // lose what the operator already typed.
      operating_hours: windows,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['screens'] })
      toast.success('Operating hours saved')
      onOpenChange(false)
    },
    onError: (error: Error) => toast.error(error.message),
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Screen operating hours</DialogTitle>
        </DialogHeader>

        <div className="max-h-[60vh] space-y-4 overflow-y-auto px-1 pt-2">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-foreground text-sm font-medium">This screen</span>
            <Select value={mode} onValueChange={(value) => setMode(value as OperatingMode)}>
              <SelectTrigger className="min-w-64"><SelectValue /></SelectTrigger>
              <SelectContent>
                {MODES.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          {mode === 'hours' && (
            <div className="space-y-2.5">
              {WEEKDAYS.map(({ key, label }) => (
                <div key={key} className="grid grid-cols-[7rem_1fr_1fr] items-center gap-3">
                  <span className="text-foreground text-sm font-medium">{label}</span>
                  <div className="space-y-1">
                    <Label htmlFor={`${key}-start`} className="text-muted-foreground text-xs">Start</Label>
                    <Input id={`${key}-start`} type="time" value={windows[key][0]} onChange={(event) => setDay(key, 0, event.target.value)} />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor={`${key}-end`} className="text-muted-foreground text-xs">End</Label>
                    <Input id={`${key}-end`} type="time" value={windows[key][1]} onChange={(event) => setDay(key, 1, event.target.value)} />
                  </div>
                </div>
              ))}
            </div>
          )}

          {mode === 'never' && (
            <p className="text-muted-foreground text-sm">The player stays on a black screen until this is changed.</p>
          )}

          {invalid.length > 0 && (
            <p className="text-destructive text-sm">
              End time must be after start time on {invalid.join(', ')}.
            </p>
          )}
        </div>

        <div className="flex justify-between pt-4">
          <Button variant="outline" onClick={() => { setMode('always'); setWindows(withDefaults(null)) }}>Reset</Button>
          <Button disabled={save.isPending || invalid.length > 0} onClick={() => save.mutate()}>
            {save.isPending ? 'Saving…' : 'Save'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
