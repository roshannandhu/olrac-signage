'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart3,
  Bell,
  ChevronDown,
  CreditCard,
  FolderCheck,
  Image as ImageIcon,
  Layers3,
  LogOut,
  MonitorPlay,
  Package,
  QrCode,
  RadioTower,
  Settings2,
  UserRound,
  Users,
} from 'lucide-react'
import { ThemeToggle } from '@/components/dashboard/theme-toggle'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuLinkItem,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { api } from '@/lib/api'
import { isSuperAdmin as roleIsSuperAdmin } from '@/lib/roles'
import { useAuthStore } from '@/lib/store'
import { useFleetAlerts } from '@/lib/use-fleet-alerts'
import { cn } from '@/lib/utils'

const primaryLinks = [
  { href: '/dashboard/content', label: 'Content', icon: ImageIcon },
  { href: '/dashboard/screens', label: 'Screens', icon: MonitorPlay },
  { href: '/dashboard/groups', label: 'Groups', icon: Layers3 },
]

const toolLinks = [
  { href: '/dashboard/campaigns', label: 'Playback report', icon: BarChart3, ownerOnly: false },
  { href: '/dashboard/alerts', label: 'Alerts', icon: Bell, ownerOnly: false },
  { href: '/dashboard/files', label: 'File management', icon: FolderCheck, ownerOnly: false },
  { href: '/dashboard/emergency', label: 'Emergency broadcast', icon: RadioTower, ownerOnly: false },
]

const accountLinks = [
  { href: '/dashboard/team', label: 'Team', icon: Users, ownerOnly: true },
  { href: '/dashboard/billing', label: 'Billing', icon: CreditCard, ownerOnly: true },
]

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const { token, user, hydrated, clearSession, setUser } = useAuthStore()
  const meQuery = useQuery({ queryKey: ['me'], queryFn: api.me, enabled: hydrated && Boolean(token) })

  // One socket for the whole dashboard, opened here so every page benefits and no page
  // opens a second one. Alerts arrive as toasts wherever the operator happens to be, which
  // is the point: previously they only existed on /dashboard/alerts, and only if you were
  // looking at it.
  useFleetAlerts()

  const isPending = (meQuery.data?.organization_status || user?.organization_status) === 'pending_approval'
  // A platform operator has no tenant workspace to manage, and every ownerOnly link below
  // is gated on role === 'owner' -- so a super_admin landing here (from a bookmark, or the
  // old post-login redirect) got a dashboard with an empty Admin menu and no way to reach
  // the console. Send them where their tools actually are.
  const isSuperAdmin = roleIsSuperAdmin(meQuery.data ?? user)

  useEffect(() => {
    if (hydrated && !token) {
      router.replace('/login')
      return
    }
    if (hydrated && token && isSuperAdmin) {
      router.replace('/admin')
      return
    }
    if (hydrated && token && isPending && pathname !== '/dashboard/pending') {
      router.replace('/dashboard/pending')
    }
  }, [hydrated, token, isSuperAdmin, isPending, pathname, router])

  useEffect(() => {
    if (meQuery.data) setUser(meQuery.data)
  }, [meQuery.data, setUser])

  const isOwner = user?.role === 'owner'
  const toolItems = toolLinks.filter((item) => !item.ownerOnly || isOwner)
  const accountItems = accountLinks.filter((item) => !item.ownerOnly || isOwner)

  const isActive = (href: string) => pathname.startsWith(href)
  const toolsActive = toolItems.some((item) => isActive(item.href))
  const logout = () => {
    clearSession()
    router.replace('/login')
  }

  if (!hydrated || !token || isSuperAdmin) {
    return <div className="bg-background min-h-screen" aria-label="Loading dashboard" />
  }

  if (isPending) {
    if (pathname !== '/dashboard/pending') {
      return <div className="bg-background min-h-screen" aria-label="Redirecting to pending verification" />
    }
    return <main className="bg-background min-h-screen">{children}</main>
  }

  return (
    <div className="bg-background min-h-screen">
      <a href="#dashboard-content" className="bg-card sr-only z-100 rounded-lg px-4 py-3 font-medium focus:not-sr-only focus:fixed focus:top-4 focus:left-4">
        Skip to content
      </a>

      <header className="border-hairline bg-card sticky top-0 z-40 border-b">
        <div className="mx-auto flex h-16 w-full max-w-[1600px] items-center gap-2 px-4 sm:px-6 lg:px-8">
          <Link href="/dashboard/screens" className="mr-4 flex shrink-0 items-center gap-2.5">
            <span className="bg-primary text-primary-foreground grid size-8 place-items-center rounded-lg">
              <RadioTower className="size-[18px]" aria-hidden="true" />
            </span>
            <span className="text-foreground hidden text-[17px] font-bold tracking-tight sm:block">Olrac Signage</span>
          </Link>

          <nav aria-label="Main" className="hidden items-center gap-1 lg:flex">
            {primaryLinks.map(({ href, label }) => (
              <Link key={href} href={href} className={cn(
                'focus-visible:ring-ring rounded-lg px-3.5 py-2 text-[15px] transition-colors focus-visible:ring-2 focus-visible:outline-none',
                isActive(href)
                  ? 'text-primary dark:text-brand font-semibold'
                  : 'text-muted-foreground hover:text-foreground font-medium',
              )}>
                {label}
              </Link>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-1">
            <DropdownMenu>
              <DropdownMenuTrigger className={cn(
                'focus-visible:ring-ring flex h-10 cursor-pointer items-center gap-1 rounded-lg px-3 text-[15px] transition-colors focus-visible:ring-2 focus-visible:outline-none',
                toolsActive ? 'text-primary dark:text-brand font-semibold' : 'text-muted-foreground hover:text-foreground font-medium',
              )}>
                Tools <ChevronDown className="size-4" aria-hidden="true" />
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                {toolItems.map(({ href, label, icon: Icon }) => (
                  <DropdownMenuLinkItem key={href} href={href} render={<Link href={href} />}>
                    <Icon aria-hidden="true" /> {label}
                  </DropdownMenuLinkItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            <ThemeToggle />

            <DropdownMenu>
              <DropdownMenuTrigger
                aria-label="Account"
                className="bg-primary text-primary-foreground focus-visible:ring-ring ml-1 grid size-9 cursor-pointer place-items-center rounded-full text-[13px] font-bold focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
              >
                {(user?.full_name || user?.username)?.slice(0, 2).toUpperCase() || '—'}
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuLabel>
                  <p className="text-foreground truncate text-sm font-semibold">{user?.full_name || user?.username || 'Account'}</p>
                  <p className="text-muted-foreground truncate text-xs">{user?.email || user?.username}</p>
                  <p className="text-muted-foreground/70 mt-0.5 truncate text-xs">
                    <span className="capitalize">{user?.role || 'Loading'}</span>
                    {user?.organization_name ? ` · ${user.organization_name}` : ''}
                  </p>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuLinkItem href="/dashboard/account" render={<Link href="/dashboard/account" />}>
                  <UserRound aria-hidden="true" /> Profile
                </DropdownMenuLinkItem>
                {accountItems.map(({ href, label, icon: Icon }) => (
                  <DropdownMenuLinkItem key={href} href={href} render={<Link href={href} />}>
                    <Icon aria-hidden="true" /> {label}
                  </DropdownMenuLinkItem>
                ))}
                <DropdownMenuLinkItem href="/dashboard/screens" render={<Link href="/dashboard/screens" />}>
                  <Settings2 aria-hidden="true" /> Manage screens
                </DropdownMenuLinkItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={logout}>
                  <LogOut aria-hidden="true" /> Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      <main id="dashboard-content" className="mx-auto w-full max-w-[1600px] px-4 py-6 pb-[calc(6rem+env(safe-area-inset-bottom))] sm:px-6 lg:px-8 lg:pb-10">
        {children}
      </main>

      <nav aria-label="Main" className="border-hairline bg-card/95 fixed inset-x-0 bottom-0 z-40 grid min-h-[72px] grid-cols-3 border-t px-2 pt-1 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl lg:hidden">
        {primaryLinks.map(({ href, label, icon: Icon }) => (
          <Link key={href} href={href} className={cn(
            'focus-visible:ring-ring flex min-w-0 flex-col items-center justify-center gap-1 text-[10px] font-semibold transition-colors focus-visible:ring-2 focus-visible:ring-inset focus-visible:outline-none',
            isActive(href) ? 'text-primary dark:text-brand' : 'text-muted-foreground',
          )}>
            <Icon className="size-5" aria-hidden="true" />
            <span className="truncate">{label}</span>
          </Link>
        ))}
      </nav>
    </div>
  )
}
