'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Clock,
  ShieldAlert,
  Tv,
  Zap,
  LogOut,
  RefreshCw,
  Sparkles,
  CheckCircle2,
  RadioTower,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { useAuthStore } from '@/lib/store'

export default function PendingApprovalPage() {
  const router = useRouter()
  const { user, token, setSession, clearSession } = useAuthStore()
  const [checking, setChecking] = useState(false)

  // Live polling every 5 seconds to automatically enter dashboard when approved
  useEffect(() => {
    if (!token) {
      router.replace('/login')
      return
    }

    const checkStatus = async () => {
      try {
        setChecking(true)
        const currentUser = await api.me()
        if (currentUser.organization_status === 'active') {
          setSession(token, currentUser)
          router.replace('/dashboard/screens')
        }
      } catch (err) {
        console.error('Status check error', err)
      } finally {
        setChecking(false)
      }
    }

    checkStatus()
    const interval = setInterval(checkStatus, 5000)
    return () => clearInterval(interval)
  }, [token, router, setSession])

  const handleLogout = () => {
    clearSession()
    router.replace('/login')
  }

  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center bg-[#070a12] p-6 text-white overflow-hidden">
      {/* Ambient background glows */}
      <div className="absolute -top-32 -left-32 size-[500px] rounded-full bg-amber-500/10 blur-[140px] pointer-events-none" />
      <div className="absolute -bottom-32 -right-32 size-[500px] rounded-full bg-emerald-500/10 blur-[140px] pointer-events-none" />

      {/* Header Brand */}
      <div className="flex items-center gap-3 mb-8">
        <div className="grid size-10 place-items-center rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 text-black shadow-lg shadow-emerald-500/20">
          <RadioTower className="size-5 text-black" />
        </div>
        <p className="font-bold tracking-wider text-lg text-white">
          OLRAC <span className="text-emerald-400 font-medium">SIGNAGE</span>
        </p>
      </div>

      {/* Main Card */}
      <div className="relative w-full max-w-xl rounded-3xl border border-white/10 bg-[#0d1322]/80 p-8 sm:p-10 shadow-2xl backdrop-blur-xl">
        {/* Status Indicator */}
        <div className="flex items-center justify-between mb-6 pb-6 border-b border-white/10">
          <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3.5 py-1.5 text-xs font-semibold text-amber-400">
            <Clock className="size-3.5 animate-spin" style={{ animationDuration: '3s' }} />
            Awaiting Manager Review
          </div>
          <div className="flex items-center gap-1.5 text-xs text-white/50">
            <RefreshCw className={`size-3 text-emerald-400 ${checking ? 'animate-spin' : ''}`} />
            Live auto-checking
          </div>
        </div>

        <h1 className="text-3xl font-bold tracking-tight text-white mb-3">
          Workspace Pending Approval
        </h1>
        <p className="text-sm leading-relaxed text-white/60 mb-6">
          Welcome <span className="font-semibold text-white">{user?.username || 'Client'}</span>! Your workspace{' '}
          <span className="font-semibold text-emerald-400">({user?.organization_name || 'Your Organization'})</span> has been created. A platform manager is reviewing your registration to allocate your fleet quota (50+ displays).
        </p>

        {/* Feature info while waiting */}
        <div className="space-y-3 mb-8 rounded-2xl bg-white/[0.03] border border-white/5 p-4 text-xs text-white/70">
          <div className="flex items-start gap-2.5">
            <CheckCircle2 className="size-4 text-emerald-400 shrink-0 mt-0.5" />
            <span>TVs signed into your account will play the <strong>OLRAC Universal Demo Reel</strong> until approved.</span>
          </div>
          <div className="flex items-start gap-2.5">
            <CheckCircle2 className="size-4 text-emerald-400 shrink-0 mt-0.5" />
            <span>The instant your account is approved, your TVs will automatically switch to your commercial loop without manual setup.</span>
          </div>
          <div className="flex items-start gap-2.5">
            <CheckCircle2 className="size-4 text-emerald-400 shrink-0 mt-0.5" />
            <span>You will receive an email confirmation as soon as full access is granted.</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3">
          <Button
            onClick={() => {
              setChecking(true)
              api.me().then((currentUser) => {
                if (currentUser.organization_status === 'active') {
                  setSession(token!, currentUser)
                  router.replace('/dashboard/screens')
                }
              }).finally(() => setChecking(false))
            }}
            disabled={checking}
            className="flex-1 bg-emerald-500 hover:bg-emerald-400 text-black font-semibold h-11 rounded-xl shadow-lg shadow-emerald-500/20"
          >
            <RefreshCw className={`size-4 mr-2 ${checking ? 'animate-spin' : ''}`} />
            {checking ? 'Checking Status...' : 'Check Approval Status'}
          </Button>

          <Button
            onClick={handleLogout}
            variant="outline"
            className="border-white/10 bg-white/5 hover:bg-white/10 text-white font-medium h-11 rounded-xl"
          >
            <LogOut className="size-4 mr-2" />
            Sign Out
          </Button>
        </div>
      </div>

      <p className="mt-8 text-xs text-white/40 text-center">
        Need priority approval? Contact support at <span className="text-emerald-400 underline">support@olracsignage.com</span>
      </p>
    </main>
  )
}
