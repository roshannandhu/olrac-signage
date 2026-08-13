'use client'

import { Monitor, Moon, Sun } from 'lucide-react'
import { useTheme } from 'next-themes'
import { useSyncExternalStore } from 'react'
import { cn } from '@/lib/utils'

const subscribe = () => () => {}

/** False during SSR and the hydration pass, true afterwards. */
function useHydrated() {
  return useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  )
}

const options = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor },
] as const

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  // Theme is only known on the client; until hydration no option reads as
  // selected, which keeps server and client markup identical.
  const hydrated = useHydrated()

  return (
    <div
      role="radiogroup"
      aria-label="Colour theme"
      className="border-rail-foreground/10 grid grid-cols-3 gap-1 rounded-xl border p-1"
    >
      {options.map(({ value, label, icon: Icon }) => {
        const active = hydrated && theme === value
        return (
          <button
            key={value}
            role="radio"
            aria-checked={active}
            aria-label={label}
            onClick={() => setTheme(value)}
            className={cn(
              'grid h-8 cursor-pointer place-items-center rounded-lg transition-colors',
              'focus-visible:ring-brand focus-visible:ring-2 focus-visible:outline-none',
              active
                ? 'bg-rail-foreground/10 text-brand'
                : 'text-rail-muted hover:bg-rail-foreground/5 hover:text-rail-foreground',
            )}
          >
            <Icon className="size-4" aria-hidden="true" />
          </button>
        )
      })}
    </div>
  )
}
