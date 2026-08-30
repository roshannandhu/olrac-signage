'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, ShieldCheck, UserRound, Users } from 'lucide-react'
import { toast } from 'sonner'
import { EmptyState } from '@/components/dashboard/empty-state'
import { ErrorState } from '@/components/dashboard/error-state'
import { PageHeader } from '@/components/dashboard/page-header'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import { relativeTime } from '@/lib/format'
import { useAuthStore } from '@/lib/store'
import type { Role, TenantRole } from '@/lib/types'

// Keyed by TenantRole, not Role: `super_admin` is a platform account, never a workspace
// member. The API filters those rows out of this list, and the backend refuses to create
// or edit one here, so the team page has no reason to describe it.
const roleDescription: Record<TenantRole, string> = {
  manager: 'Approvals and fleet management',
  owner: 'Full access, including team management',
  editor: 'Can publish and manage signage content',
  viewer: 'Read-only access to network status',
}

const TENANT_ROLES: TenantRole[] = ['manager', 'owner', 'editor', 'viewer']

/** Narrow an API-supplied role for display; a platform account should never appear. */
const asTenantRole = (role: Role): TenantRole => (role === 'super_admin' ? 'viewer' : role)

export default function TeamPage() {
  const queryClient = useQueryClient()
  const currentUser = useAuthStore((state) => state.user)
  const usersQuery = useQuery({ queryKey: ['users'], queryFn: api.getUsers, enabled: currentUser?.role === 'owner' })
  const [open, setOpen] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<TenantRole>('viewer')

  const createMutation = useMutation({
    mutationFn: () => api.createUser({ username: username.trim(), password, role }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['users'] }); toast.success('Team member added'); setOpen(false); setUsername(''); setPassword(''); setRole('viewer') },
    onError: (error: Error) => toast.error(error.message),
  })
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { role?: TenantRole; is_active?: boolean } }) => api.updateUser(id, data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['users'] }); toast.success('Access updated') },
    onError: (error: Error) => toast.error(error.message),
  })

  if (currentUser && currentUser.role !== 'owner') return <ErrorState message="Only workspace owners can manage team access." onRetry={() => window.history.back()} />
  if (usersQuery.isError) return <ErrorState message="Team access could not be loaded." onRetry={() => usersQuery.refetch()} />
  const users = usersQuery.data || []

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Access control" title="Team" description="Give each operator exactly the permissions they need. Accounts can be disabled immediately without shared passwords." actions={
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger render={<Button />}><Plus data-icon="inline-start" /> Add member</DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Add team member</DialogTitle><DialogDescription>Create an individual account and choose its workspace role.</DialogDescription></DialogHeader>
            <form onSubmit={(event) => { event.preventDefault(); createMutation.mutate() }} className="space-y-4 pt-2">
              <div className="space-y-2"><Label htmlFor="team-username">Username</Label><Input id="team-username" value={username} onChange={(event) => setUsername(event.target.value)} minLength={3} placeholder="alex" required /></div>
              <div className="space-y-2"><Label htmlFor="team-password">Temporary password</Label><Input id="team-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} minLength={8} autoComplete="new-password" placeholder="At least 8 characters" required /></div>
              <div className="space-y-2"><Label>Role</Label><Select value={role} onValueChange={(value: TenantRole | null) => value && setRole(value)}><SelectTrigger className="w-full"><SelectValue>{(value: TenantRole | null) => value ? value[0].toUpperCase() + value.slice(1) : 'Choose role'}</SelectValue></SelectTrigger><SelectContent>{TENANT_ROLES.map((value) => <SelectItem key={value} value={value}><span className="capitalize">{value}</span></SelectItem>)}</SelectContent></Select><p className="text-xs text-muted-foreground/70">{roleDescription[role]}</p></div>
              <Button type="submit" className="w-full" disabled={username.trim().length < 3 || password.length < 8 || createMutation.isPending}>{createMutation.isPending ? 'Creating…' : 'Create account'}</Button>
            </form>
          </DialogContent>
        </Dialog>
      } />

      {usersQuery.isLoading ? <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 3 }).map((_, index) => <Skeleton key={index} className="h-64" />)}</div> : !users.length ? <EmptyState icon={Users} title="No team members" description="Create the first individual account for your signage operators." /> : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {users.map((user) => <Card key={user.id} className="border-0 bg-card py-0 shadow-[0_1px_2px_rgba(15,23,42,.04)] ring-1 ring-hairline"><CardContent className="p-5"><div className="flex items-start gap-3"><span className="grid size-11 place-items-center rounded-xl bg-primary/10 text-primary dark:text-brand"><UserRound className="size-5" /></span><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h2 className="truncate font-semibold text-foreground">{user.username}</h2>{user.id === currentUser?.id && <Badge variant="secondary">You</Badge>}</div><p className="mt-1 text-xs text-muted-foreground/70">Added {relativeTime(user.created_at)}</p></div><Badge variant={user.is_active ? 'success' : 'danger'}>{user.is_active ? 'Active' : 'Disabled'}</Badge></div><div className="mt-5 space-y-2"><Label className="text-xs text-muted-foreground">Workspace role</Label><Select value={asTenantRole(user.role)} disabled={updateMutation.isPending} onValueChange={(value: TenantRole | null) => value && updateMutation.mutate({ id: user.id, data: { role: value } })}><SelectTrigger className="w-full"><SelectValue>{(value: TenantRole | null) => value ? value[0].toUpperCase() + value.slice(1) : 'Role'}</SelectValue></SelectTrigger><SelectContent>{TENANT_ROLES.map((value) => <SelectItem key={value} value={value}><span className="capitalize">{value}</span></SelectItem>)}</SelectContent></Select><p className="text-xs leading-5 text-muted-foreground/70">{roleDescription[asTenantRole(user.role)]}</p></div><div className="mt-5 flex items-center justify-between border-t border-hairline pt-4"><span className="flex items-center gap-2 text-xs text-muted-foreground"><ShieldCheck className="size-3.5" /> Individual login</span><Button size="sm" variant={user.is_active ? 'outline' : 'secondary'} disabled={user.id === currentUser?.id || updateMutation.isPending} onClick={() => updateMutation.mutate({ id: user.id, data: { is_active: !user.is_active } })}>{user.is_active ? 'Disable' : 'Enable'}</Button></div></CardContent></Card>)}
        </div>
      )}
    </div>
  )
}
