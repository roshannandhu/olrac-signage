'use client'

import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Copy, Key, Plus, ShieldAlert, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { EmptyState } from '@/components/dashboard/empty-state'
import { ErrorState } from '@/components/dashboard/error-state'
import { PageHeader } from '@/components/dashboard/page-header'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import { relativeTime } from '@/lib/format'
import { useAuthStore } from '@/lib/store'
import type { EnrollmentToken } from '@/lib/types'

export default function EnrollmentPage() {
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)
  const isOwner = user?.role === 'owner'
  
  const tokensQuery = useQuery({ queryKey: ['enrollment-tokens'], queryFn: api.getEnrollmentTokens, enabled: isOwner })
  const tokens = useMemo(() => tokensQuery.data || [], [tokensQuery.data])

  const [createOpen, setCreateOpen] = useState(false)
  const [description, setDescription] = useState('')
  const [maxUses, setMaxUses] = useState('')
  const [expiresAt, setExpiresAt] = useState('')
  const [createdToken, setCreatedToken] = useState<EnrollmentToken | null>(null)

  const createMutation = useMutation({
    mutationFn: (data: { description?: string, expires_at?: string, max_uses?: number }) => api.createEnrollmentToken(data),
    onSuccess: (token) => {
      queryClient.invalidateQueries({ queryKey: ['enrollment-tokens'] })
      toast.success('Token created')
      setCreatedToken(token)
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const revokeMutation = useMutation({
    mutationFn: api.revokeEnrollmentToken,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['enrollment-tokens'] })
      toast.success('Token revoked')
    },
    onError: (error: Error) => toast.error(error.message),
  })

  if (!isOwner) {
    return <ErrorState message="Only workspace owners can manage enrollment tokens." onRetry={() => {}} />
  }

  if (tokensQuery.isError) {
    return <ErrorState message="Tokens could not be loaded." onRetry={() => tokensQuery.refetch()} />
  }

  const handleCreate = () => {
    createMutation.mutate({
      description: description.trim() || undefined,
      max_uses: maxUses ? parseInt(maxUses, 10) : undefined,
      expires_at: expiresAt ? new Date(expiresAt).toISOString() : undefined,
    })
  }

  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      toast.success('Copied to clipboard')
    } catch {
      toast.error('Failed to copy')
    }
  }

  const handleCloseCreate = (open: boolean) => {
    if (!open) {
      if (createdToken) {
        setCreatedToken(null)
      }
      setCreateOpen(false)
      setDescription('')
      setMaxUses('')
      setExpiresAt('')
    } else {
      setCreateOpen(true)
    }
  }

  const actions = (
    <Dialog open={createOpen} onOpenChange={handleCloseCreate}>
      <DialogTrigger render={<Button><Plus className="mr-2 h-4 w-4" /> New token</Button>} />
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Create enrollment token</DialogTitle>
          <DialogDescription>
            Tokens allow new displays to securely join your fleet without logging in.
          </DialogDescription>
        </DialogHeader>
        {createdToken ? (
          <div className="space-y-5 pt-2">
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-700 dark:text-amber-300 flex gap-3">
              <ShieldAlert className="size-5 shrink-0" />
              <div>
                <p className="font-semibold">Copy this token now</p>
                <p className="mt-1">For security, you will not be able to see it again after closing this window.</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Input readOnly value={createdToken.token || ''} className="font-mono" />
              <Button size="icon" variant="outline" onClick={() => handleCopy(createdToken.token || '')}>
                <Copy className="size-4" />
              </Button>
            </div>
            <Button className="w-full mt-4" onClick={() => handleCloseCreate(false)}>Done</Button>
          </div>
        ) : (
          <div className="space-y-4 pt-2">
            <div className="space-y-2">
              <Label htmlFor="description">Description (optional)</Label>
              <Input id="description" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="e.g. New York Office" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="max_uses">Max Uses (optional)</Label>
                <Input id="max_uses" type="number" min="1" value={maxUses} onChange={(e) => setMaxUses(e.target.value)} placeholder="Unlimited" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="expires_at">Expires (optional)</Label>
                <Input id="expires_at" type="datetime-local" value={expiresAt} onChange={(e) => setExpiresAt(e.target.value)} />
              </div>
            </div>
            <Button className="w-full mt-2" disabled={createMutation.isPending} onClick={handleCreate}>
              {createMutation.isPending ? 'Creating…' : 'Generate Token'}
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Security" title="Enrollment Tokens" description="Manage credentials used by physical devices to securely enrol into this workspace." actions={actions} />
      
      {tokensQuery.isLoading ? (
        <div className="grid gap-4"><Skeleton className="h-20" /><Skeleton className="h-20" /><Skeleton className="h-20" /></div>
      ) : !tokens.length ? (
        <EmptyState icon={Key} title="No tokens generated" description="Create an enrollment token to securely add unauthenticated TVs to your fleet." action={<Button onClick={() => setCreateOpen(true)}><Plus className="mr-2 h-4 w-4" /> Create first token</Button>} />
      ) : (
        <div className="rounded-xl border border-hairline bg-card overflow-hidden">
          <div className="grid grid-cols-[1fr_minmax(120px,auto)_minmax(120px,auto)_minmax(150px,auto)_minmax(80px,auto)_minmax(80px,auto)] gap-4 border-b border-hairline bg-muted/50 p-4 text-xs font-medium text-muted-foreground">
            <div>Description</div>
            <div>Token</div>
            <div>Uses</div>
            <div>Expires</div>
            <div>Status</div>
            <div className="text-right">Actions</div>
          </div>
          <div className="divide-y divide-hairline">
            {tokens.map((token) => (
              <div key={token.id} className="grid items-center grid-cols-[1fr_minmax(120px,auto)_minmax(120px,auto)_minmax(150px,auto)_minmax(80px,auto)_minmax(80px,auto)] gap-4 p-4 text-sm">
                <div className="font-medium">{token.description || '—'}</div>
                <div className="font-mono text-muted-foreground">{token.token}</div>
                <div>
                  <span className="font-medium">{token.use_count}</span>
                  <span className="text-muted-foreground"> / {token.max_uses ? token.max_uses : '∞'}</span>
                </div>
                <div className="text-muted-foreground">{token.expires_at ? relativeTime(token.expires_at) : 'Never'}</div>
                <div>
                  <Badge variant={token.is_active ? 'success' : 'outline'} className={token.is_active ? undefined : 'text-muted-foreground'}>
                    {token.is_active ? 'Active' : 'Revoked'}
                  </Badge>
                </div>
                <div className="text-right">
                  {token.is_active && (
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive hover:bg-destructive/10" title="Revoke token" onClick={() => revokeMutation.mutate(token.id)} disabled={revokeMutation.isPending}>
                      <Trash2 className="size-4" />
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
