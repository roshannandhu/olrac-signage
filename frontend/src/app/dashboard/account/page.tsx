'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Building2, KeyRound, UserRound } from 'lucide-react'
import { toast } from 'sonner'
import { ErrorState } from '@/components/dashboard/error-state'
import { PageHeader } from '@/components/dashboard/page-header'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import { useAuthStore } from '@/lib/store'

const cardClass = 'border-0 bg-card py-0 shadow-[0_1px_2px_rgba(15,23,42,.04)] ring-1 ring-hairline'

export default function AccountPage() {
  const queryClient = useQueryClient()
  const setUser = useAuthStore((state) => state.setUser)
  const meQuery = useQuery({ queryKey: ['me'], queryFn: api.me })

  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  // Seed the form once the profile arrives, keyed on the record's identity rather than the
  // whole object so a background refetch cannot overwrite what is being typed.
  //
  // Adjusted during render rather than in an effect. An effect runs after paint, so the
  // inputs flashed empty for a frame before filling in, and it tripped
  // react-hooks/set-state-in-effect. React re-runs the component immediately on a
  // set-during-render and never commits the intermediate output, so this is the pattern
  // React documents for deriving state from a changed input.
  const [seededId, setSeededId] = useState<number | null>(null)
  if (meQuery.data && meQuery.data.id !== seededId) {
    setSeededId(meQuery.data.id)
    setFullName(meQuery.data.full_name || '')
    setEmail(meQuery.data.email || '')
  }

  const profileMutation = useMutation({
    mutationFn: () =>
      api.updateProfile({
        full_name: fullName.trim() || null,
        email: email.trim() || null,
      }),
    onSuccess: (user) => {
      setUser(user)
      queryClient.invalidateQueries({ queryKey: ['me'] })
      toast.success('Profile updated')
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const passwordMutation = useMutation({
    mutationFn: () => api.changePassword({ current_password: currentPassword, new_password: newPassword }),
    onSuccess: () => {
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      toast.success('Password changed')
    },
    onError: (error: Error) => toast.error(error.message),
  })

  if (meQuery.isError) {
    return <ErrorState message="Your account could not be loaded." onRetry={() => meQuery.refetch()} />
  }

  const user = meQuery.data
  const passwordsMatch = newPassword === confirmPassword
  const canSubmitPassword =
    currentPassword.length > 0 &&
    newPassword.length >= 8 &&
    passwordsMatch &&
    newPassword !== currentPassword &&
    !passwordMutation.isPending

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Your account"
        title="Profile"
        description="Update how you appear across the workspace and change the password for this account."
      />

      {meQuery.isLoading || !user ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-80" />
          <Skeleton className="h-80" />
        </div>
      ) : (
        <div className="grid items-start gap-6 lg:grid-cols-2">
          <Card className={cardClass}>
            <CardContent className="space-y-6 p-6">
              <div className="flex items-center gap-4">
                <span className="bg-primary text-primary-foreground grid size-12 shrink-0 place-items-center rounded-full text-base font-bold">
                  {(user.full_name || user.username).slice(0, 2).toUpperCase()}
                </span>
                <div className="min-w-0">
                  <p className="text-foreground truncate text-[15px] font-semibold">
                    {user.full_name || user.username}
                  </p>
                  <div className="mt-1 flex flex-wrap items-center gap-2">
                    <Badge className="capitalize">{user.role}</Badge>
                    {user.organization_name ? (
                      <span className="text-muted-foreground inline-flex items-center gap-1 text-xs">
                        <Building2 className="size-3.5" aria-hidden="true" />
                        {user.organization_name}
                      </span>
                    ) : null}
                  </div>
                </div>
              </div>

              <form
                onSubmit={(event) => {
                  event.preventDefault()
                  profileMutation.mutate()
                }}
                className="space-y-4"
              >
                <div className="space-y-2">
                  <Label htmlFor="account-username">Username</Label>
                  <Input id="account-username" value={user.username} readOnly disabled />
                  <p className="text-muted-foreground/70 text-xs">
                    Your sign-in name. Only an owner can change it, from Team.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="account-name">Full name</Label>
                  <Input
                    id="account-name"
                    value={fullName}
                    onChange={(event) => setFullName(event.target.value)}
                    maxLength={120}
                    placeholder="Alex Fernandes"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="account-email">Email</Label>
                  <Input
                    id="account-email"
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="alex@example.com"
                  />
                </div>
                <Button type="submit" disabled={profileMutation.isPending}>
                  <UserRound data-icon="inline-start" />
                  {profileMutation.isPending ? 'Saving…' : 'Save profile'}
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card className={cardClass}>
            <CardContent className="space-y-6 p-6">
              <div>
                <h2 className="text-foreground text-[15px] font-semibold">Change password</h2>
                <p className="text-muted-foreground mt-1 text-sm">
                  You will stay signed in on this device. Other devices keep their existing session
                  until it expires.
                </p>
              </div>

              <form
                onSubmit={(event) => {
                  event.preventDefault()
                  passwordMutation.mutate()
                }}
                className="space-y-4"
              >
                <div className="space-y-2">
                  <Label htmlFor="account-current">Current password</Label>
                  <Input
                    id="account-current"
                    type="password"
                    autoComplete="current-password"
                    value={currentPassword}
                    onChange={(event) => setCurrentPassword(event.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="account-new">New password</Label>
                  <Input
                    id="account-new"
                    type="password"
                    autoComplete="new-password"
                    value={newPassword}
                    onChange={(event) => setNewPassword(event.target.value)}
                    minLength={8}
                    placeholder="At least 8 characters"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="account-confirm">Confirm new password</Label>
                  <Input
                    id="account-confirm"
                    type="password"
                    autoComplete="new-password"
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    minLength={8}
                    required
                  />
                  {confirmPassword.length > 0 && !passwordsMatch ? (
                    <p className="text-destructive text-xs">Passwords do not match.</p>
                  ) : null}
                </div>
                <Button type="submit" disabled={!canSubmitPassword}>
                  <KeyRound data-icon="inline-start" />
                  {passwordMutation.isPending ? 'Changing…' : 'Change password'}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
