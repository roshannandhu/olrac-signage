'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowRight, CheckCircle2, RadioTower, ShieldCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api } from '@/lib/api'
import { useAuthStore } from '@/lib/store'

export default function LoginPage() {
  const router = useRouter()
  const { token, hydrated, setSession } = useAuthStore()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)

  useEffect(() => {
    if (hydrated && token) router.replace('/dashboard')
  }, [hydrated, token, router])

  const handleLogin = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')
    setPending(true)
    try {
      const session = await api.login(username.trim(), password)
      setSession(session.access_token, session.user)
      router.replace('/dashboard')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Sign in failed')
    } finally {
      setPending(false)
    }
  }

  return (
    <main className="grid min-h-screen bg-rail lg:grid-cols-[1.08fr_.92fr]">
      <section className="signal-grid relative hidden overflow-hidden border-r border-white/10 p-12 text-white lg:flex lg:flex-col lg:justify-between xl:p-16">
        <div className="absolute -left-28 top-1/3 size-80 rounded-full bg-brand/10 blur-3xl" aria-hidden="true" />
        <div className="relative flex items-center gap-3">
          <span className="grid size-11 place-items-center rounded-2xl bg-brand text-rail"><RadioTower className="size-5" /></span>
          <div><p className="font-bold tracking-[0.1em]">OLRAC</p><p className="text-rail-muted text-xs tracking-[0.2em] uppercase">Signage control</p></div>
        </div>
        <div className="relative max-w-xl">
          <p className="mb-5 text-xs font-bold uppercase tracking-[0.22em] text-brand">Every screen. One signal.</p>
          <h1 className="text-balance text-5xl font-semibold leading-[1.04] tracking-[-0.045em] xl:text-6xl">Your network, live and in sync.</h1>
          <p className="mt-6 max-w-lg text-lg leading-8 text-white/55">Schedule campaigns, group displays, and keep every player current from one resilient control plane.</p>
          <div className="mt-10 grid max-w-lg grid-cols-2 gap-4 text-sm text-white/60">
            <div className="flex items-center gap-2"><CheckCircle2 className="size-4 text-brand" /> Offline-ready playback</div>
            <div className="flex items-center gap-2"><ShieldCheck className="size-4 text-brand" /> Role-based access</div>
          </div>
        </div>
        <p className="relative text-xs text-white/30">OLRAC Signage · Operations portal</p>
      </section>

      <section className="flex items-center justify-center bg-background px-5 py-12 sm:px-10">
        <div className="w-full max-w-[420px]">
          <div className="mb-9 flex items-center gap-3 lg:hidden">
            <span className="grid size-10 place-items-center rounded-xl bg-brand text-rail"><RadioTower className="size-5" /></span>
            <span className="font-bold tracking-[0.1em]">OLRAC</span>
          </div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary">Secure access</p>
          <h2 className="mt-3 text-4xl font-semibold tracking-[-0.04em] text-foreground">Welcome back</h2>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">Sign in with the account created by your workspace owner.</p>

          <form onSubmit={handleLogin} className="mt-9 space-y-5">
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input id="username" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} placeholder="your-name" required className="h-12 bg-card" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="••••••••" required className="h-12 bg-card" />
            </div>
            {error && <p role="alert" className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-700 dark:text-rose-300">{error}</p>}
            <Button type="submit" size="lg" className="h-12 w-full bg-primary text-primary-foreground hover:bg-primary/90" disabled={pending || !username.trim() || !password}>
              {pending ? 'Signing in…' : <>Sign in <ArrowRight data-icon="inline-end" /></>}
            </Button>
          </form>
          <p className="mt-7 text-center text-xs leading-5 text-muted-foreground/70">No default credentials are enabled. Contact your workspace owner if you need access.</p>
        </div>
      </section>
    </main>
  )
}
