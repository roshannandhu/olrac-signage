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
  const [googleEnabled, setGoogleEnabled] = useState(false)

  useEffect(() => {
    if (hydrated && token) router.replace('/dashboard')
  }, [hydrated, token, router])

  // Only draw the Google button if this deployment actually has the browser OAuth client.
  // Otherwise it is a button whose one possible outcome is a 503.
  useEffect(() => {
    api.authMethods().then((methods) => setGoogleEnabled(methods.google))
  }, [])

  // Google sends the browser back here with ?code=. Exchange it once, server-side, then
  // strip it from the URL so a refresh cannot replay a code that Google has already spent.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')
    const denied = params.get('error')
    if (denied) {
      setError('Google sign-in was cancelled.')
      window.history.replaceState({}, '', window.location.pathname)
      return
    }
    if (!code) return

    setPending(true)
    const redirectUri = `${window.location.origin}${window.location.pathname}`
    window.history.replaceState({}, '', window.location.pathname)
    api
      .loginWithGoogle(code, redirectUri)
      .then((session) => {
        setSession(session.access_token, session.user)
        router.replace('/dashboard')
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : 'Google sign-in failed'))
      .finally(() => setPending(false))
  }, [router, setSession])

  const startGoogle = () => {
    const redirectUri = `${window.location.origin}/login`
    const query = new URLSearchParams({
      client_id: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '',
      redirect_uri: redirectUri,
      response_type: 'code',
      scope: 'openid email profile',
      // Identity only, so no refresh token is wanted and no consent screen is forced.
      prompt: 'select_account',
    })
    window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?${query}`
  }

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
    <main className="grid grid-cols-1 min-h-screen bg-rail lg:grid-cols-[1.08fr_.92fr]">
      <section className="relative hidden overflow-hidden border-r border-white/10 p-12 text-white lg:flex lg:flex-col lg:justify-between xl:p-16">
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
          {googleEnabled && (
            <>
              <div className="my-6 flex items-center gap-4">
                <span className="h-px flex-1 bg-border" />
                <span className="text-xs text-muted-foreground">or</span>
                <span className="h-px flex-1 bg-border" />
              </div>
              <Button
                type="button"
                variant="outline"
                size="lg"
                className="h-12 w-full"
                onClick={startGoogle}
                disabled={pending}
              >
                <svg className="size-5" viewBox="0 0 24 24" aria-hidden="true">
                  <path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5a5.6 5.6 0 0 1-2.4 3.7v3h3.9c2.3-2.1 3.5-5.2 3.5-8.9z" />
                  <path fill="#34A853" d="M12 24c3.2 0 5.9-1.1 7.9-2.9l-3.9-3c-1.1.7-2.4 1.2-4 1.2-3.1 0-5.7-2.1-6.6-4.9H1.4v3.1A12 12 0 0 0 12 24z" />
                  <path fill="#FBBC05" d="M5.4 14.4a7.2 7.2 0 0 1 0-4.6V6.7H1.4a12 12 0 0 0 0 10.8l4-3.1z" />
                  <path fill="#EA4335" d="M12 4.8c1.8 0 3.3.6 4.6 1.8l3.4-3.4A12 12 0 0 0 1.4 6.7l4 3.1C6.3 6.9 8.9 4.8 12 4.8z" />
                </svg>
                Sign in with Google
              </Button>
            </>
          )}
          <p className="mt-7 text-center text-xs leading-5 text-muted-foreground/70">No default credentials are enabled. Contact your workspace owner if you need access.</p>
        </div>
      </section>
    </main>
  )
}
