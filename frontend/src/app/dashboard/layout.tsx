'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Image as ImageIcon,
  AlertTriangle,
  BarChart3,
  CreditCard,
  Key,
  LayoutDashboard,
  ListVideo,
  LogOut,
  MonitorPlay,
  Package,
  RadioTower,
  Users,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { ThemeToggle } from '@/components/dashboard/theme-toggle'
import { api } from '@/lib/api'
import { useAuthStore } from '@/lib/store'
import { cn } from '@/lib/utils'

const primaryLinks = [
  { href: '/dashboard', label: 'Overview', icon: LayoutDashboard },
  { href: '/dashboard/screens', label: 'Screens', icon: MonitorPlay },
  { href: '/dashboard/content', label: 'Library', icon: ImageIcon },
  { href: '/dashboard/playlists', label: 'Playlists', icon: ListVideo },
  { href: '/dashboard/campaigns', label: 'Campaigns', icon: BarChart3 },
  { href: '/dashboard/releases', label: 'Releases', icon: Package },
  { href: '/dashboard/emergency', label: 'Emergency', icon: AlertTriangle },
]

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const { token, user, hydrated, clearSession, setUser } = useAuthStore()
  const meQuery = useQuery({ queryKey: ['me'], queryFn: api.me, enabled: hydrated && Boolean(token) })

  useEffect(() => {
    if (hydrated && !token) router.replace('/login')
  }, [hydrated, token, router])

  useEffect(() => {
    if (meQuery.data) setUser(meQuery.data)
  }, [meQuery.data, setUser])

  const links = user?.role === 'owner'
    ? [...primaryLinks, { href: '/dashboard/enrollment', label: 'Enrollment', icon: Key }, { href: '/dashboard/team', label: 'Team', icon: Users }, { href: '/dashboard/billing', label: 'Billing', icon: CreditCard }]
    : primaryLinks

  const isActive = (href: string) => href === '/dashboard' ? pathname === href : pathname.startsWith(href)
  const logout = () => {
    clearSession()
    router.replace('/login')
  }

  if (!hydrated || !token) {
    return <div className="bg-rail min-h-screen" aria-label="Loading dashboard" />
  }

  return (
    <div className="bg-background min-h-screen lg:grid lg:grid-cols-[248px_1fr]">
      <a href="#dashboard-content" className="bg-card sr-only z-[100] rounded-lg px-4 py-3 font-medium focus:not-sr-only focus:fixed focus:top-4 focus:left-4">
        Skip to content
      </a>

      <aside className="bg-rail text-rail-foreground hidden min-h-screen flex-col lg:sticky lg:top-0 lg:flex lg:h-screen">
        <div className="border-rail-foreground/10 flex h-20 items-center gap-3 border-b px-6">
          <span className="bg-brand text-rail grid size-10 place-items-center rounded-xl shadow-[0_0_30px_rgba(45,212,191,.18)]">
            <RadioTower className="size-5" aria-hidden="true" />
          </span>
          <div>
            <p className="text-[15px] font-bold tracking-[0.08em]">OLRAC</p>
            <p className="text-brand/60 text-[10px] tracking-[0.22em] uppercase">Signage control</p>
          </div>
        </div>

        <nav aria-label="Dashboard" className="flex-1 px-3 py-6">
          <p className="text-rail-muted/60 mb-3 px-3 text-[10px] font-bold tracking-[0.2em] uppercase">Workspace</p>
          <div className="space-y-1">
            {links.map(({ href, label, icon: Icon }) => (
              <Link key={href} href={href} className={cn(
                'focus-visible:ring-brand flex h-11 items-center gap-3 rounded-xl px-3 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:outline-none',
                isActive(href)
                  ? 'bg-rail-foreground/10 text-rail-foreground'
                  : 'text-rail-muted hover:bg-rail-foreground/[.06] hover:text-rail-foreground',
              )}>
                <Icon className={cn('size-[18px]', isActive(href) && 'text-brand')} aria-hidden="true" />
                {label}
                {isActive(href) && <span className="bg-brand ml-auto size-1.5 rounded-full" aria-hidden="true" />}
              </Link>
            ))}
          </div>
        </nav>

        <div className="border-rail-foreground/10 space-y-3 border-t p-4">
          <div className="bg-rail-foreground/[.045] flex items-center gap-3 rounded-xl p-3">
            <div className="bg-rail-foreground/10 text-brand grid size-9 place-items-center rounded-lg text-sm font-bold">
              {user?.username.slice(0, 2).toUpperCase() || '—'}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{user?.username || 'Account'}</p>
              <p className="text-rail-muted/70 text-xs capitalize">{user?.role || 'Loading'}</p>
            </div>
          </div>
          <ThemeToggle />
          <button onClick={logout} className="text-rail-muted hover:bg-rail-foreground/[.06] hover:text-rail-foreground focus-visible:ring-brand flex h-10 w-full cursor-pointer items-center gap-3 rounded-lg px-3 text-sm transition-colors focus-visible:ring-2 focus-visible:outline-none">
            <LogOut className="size-4" aria-hidden="true" /> Sign out
          </button>
        </div>
      </aside>

      <div className="min-w-0 pb-20 lg:pb-0">
        <header className="border-hairline bg-background/90 sticky top-0 z-30 flex h-16 items-center justify-between border-b px-4 backdrop-blur-xl sm:px-6 lg:hidden">
          <Link href="/dashboard" className="text-foreground flex items-center gap-2 font-bold tracking-[0.08em]">
            <span className="bg-brand text-rail grid size-8 place-items-center rounded-lg"><RadioTower className="size-4" /></span>
            OLRAC
          </Link>
          <Badge variant="outline" className="capitalize">{user?.role}</Badge>
        </header>

        <main id="dashboard-content" className="mx-auto w-full max-w-[1500px] px-4 py-7 sm:px-6 sm:py-9 lg:px-10 lg:py-10">
          {children}
        </main>
      </div>

      <nav aria-label="Mobile dashboard" className="border-hairline bg-card/95 fixed inset-x-0 bottom-0 z-40 grid h-[72px] border-t px-2 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl lg:hidden" style={{ gridTemplateColumns: `repeat(${Math.min(links.length, 6)}, minmax(0, 1fr))` }}>
        {links.slice(0, 6).map(({ href, label, icon: Icon }) => (
          <Link key={href} href={href} className={cn(
            'focus-visible:ring-brand flex min-w-0 flex-col items-center justify-center gap-1 text-[10px] font-semibold transition-colors focus-visible:ring-2 focus-visible:ring-inset focus-visible:outline-none',
            isActive(href) ? 'text-primary' : 'text-muted-foreground',
          )}>
            <Icon className="size-5" aria-hidden="true" />
            <span className="truncate">{label}</span>
          </Link>
        ))}
      </nav>
    </div>
  )
}
