import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStore } from '../store'
import { useLogin } from '../hooks'

// Demo mode: Supabase not yet configured (env var missing or still placeholder)
const SUPABASE_CONFIGURED =
  !!import.meta.env.VITE_SUPABASE_URL &&
  !(import.meta.env.VITE_SUPABASE_URL as string).includes('YOUR-PROJECT')

export default function Login() {
  const pushToast = useStore((s) => s.pushToast)
  const login = useStore((s) => s.login)
  const nav = useNavigate()
  const [email, setEmail] = useState('admin@olrac.com')
  const [password, setPassword] = useState('OlracAdmin!2026')
  const { mutate, isPending } = useLogin()

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim() || !password.trim()) {
      pushToast('Enter email and password', 'error')
      return
    }
    if (!SUPABASE_CONFIGURED) {
      login()
      pushToast('Welcome back!', 'success')
      nav('/')
      return
    }
    mutate({ email, password }, { onSuccess: () => nav('/') })
  }

  return (
    <div className="login-wrap">
      <div className="login-bg" />
      <form className="login-card" onSubmit={submit}>
        <div className="login-brand">
          <div className="sb-badge" style={{ marginBottom: 0 }}>
            <div className="sb-icon">📺</div>
            <span className="sb-name">Olrac</span>
          </div>
        </div>
        <div className="login-title">Sign in to Olrac Signage</div>
        <div className="login-sub">Manage your screens, content and playlists.</div>
        <div className="fg">
          <label className="fl">Email</label>
          <input
            className="fi2"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
            disabled={isPending}
          />
        </div>
        <div className="fg">
          <label className="fl">Password</label>
          <input
            className="fi2"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            disabled={isPending}
          />
        </div>
        <button
          className="btn btn-p"
          type="submit"
          disabled={isPending}
          style={{ width: '100%', justifyContent: 'center', padding: '9px', marginTop: 4 }}
        >
          {isPending ? 'Signing in…' : 'Sign in'}
        </button>
        <div className="login-hint">
          {SUPABASE_CONFIGURED
            ? 'Enter your Supabase credentials to sign in'
            : 'Demo build · pre-filled credentials'}
        </div>
      </form>
    </div>
  )
}
