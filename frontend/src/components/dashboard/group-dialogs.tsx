'use client'

import { useMemo, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { StatusIndicator } from '@/components/dashboard/status-indicator'
import { api } from '@/lib/api'
import type { Screen, ScreenGroup } from '@/lib/types'

/** Which screens follow this group's playlist. Edited as a set, saved once. */
export function AssignScreensDialog({
  group,
  screens,
  open,
  onOpenChange,
}: {
  group: ScreenGroup
  screens: Screen[]
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const queryClient = useQueryClient()
  const members = useMemo(() => screens.filter((s) => s.group_id === group.id).map((s) => s.id), [screens, group.id])
  // null means untouched, so the list tracks the server until the operator edits it.
  const [edited, setEdited] = useState<number[] | null>(null)
  const selected = edited ?? members
  const dirty = edited !== null

  const save = useMutation({
    mutationFn: () => api.setGroupScreens(group.id, selected),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['groups'] })
      queryClient.invalidateQueries({ queryKey: ['screens'] })
      toast.success('Screens assigned')
      setEdited(null)
      onOpenChange(false)
    },
    onError: (error: Error) => toast.error(error.message),
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Assign screens</DialogTitle>
          <DialogDescription>Every screen you tick plays this group&apos;s playlist.</DialogDescription>
        </DialogHeader>
        <div className="max-h-[55vh] space-y-1 overflow-y-auto px-1 pt-2">
          {!screens.length && <p className="text-muted-foreground p-2 text-sm">No screens paired yet.</p>}
          {screens.map((screen) => {
            const elsewhere = screen.group_id !== null && screen.group_id !== group.id
            return (
              <label key={screen.id} className="hover:bg-muted flex cursor-pointer items-center gap-3 rounded-lg p-2.5 text-sm">
                <input
                  type="checkbox"
                  className="accent-primary size-4"
                  checked={selected.includes(screen.id)}
                  onChange={(event) => setEdited(event.target.checked
                    ? [...selected, screen.id]
                    : selected.filter((id) => id !== screen.id))}
                />
                <span className="min-w-0 flex-1 truncate">{screen.name || `Screen ${screen.id}`}</span>
                {elsewhere && selected.includes(screen.id) && <Badge variant="warning">moves here</Badge>}
                <StatusIndicator status={screen.status} />
              </label>
            )
          })}
        </div>
        <DialogFooter showCloseButton>
          <Button disabled={!dirty || save.isPending} onClick={() => save.mutate()}>
            {save.isPending ? 'Saving…' : 'Save'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

/** Name and description, mirroring the screen settings dialog. */
export function GroupSettingsDialog({
  group,
  open,
  onOpenChange,
}: {
  group: ScreenGroup
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const queryClient = useQueryClient()
  const [name, setName] = useState(group.name)

  const save = useMutation({
    mutationFn: () => api.renameGroup(group.id, name.trim()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['groups'] })
      toast.success('Group settings saved')
      onOpenChange(false)
    },
    onError: (error: Error) => toast.error(error.message),
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Group settings</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 pt-2">
          <div className="space-y-2">
            <Label htmlFor="group-settings-name">Name <span className="text-destructive">*</span></Label>
            <Input id="group-settings-name" value={name} onChange={(event) => setName(event.target.value)} autoFocus />
          </div>
        </div>
        <DialogFooter showCloseButton>
          <Button disabled={!name.trim() || save.isPending} onClick={() => save.mutate()}>
            {save.isPending ? 'Saving…' : 'Save'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
