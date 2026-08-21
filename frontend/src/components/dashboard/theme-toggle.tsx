'use client'

import { Moon, Sun } from 'lucide-react'
import { useTheme } from 'next-themes'
import { useSyncExternalStore } from 'react'

const subscribe = () => () => {}

/** False during SSR and the hydration pass, true afterwards. */
function useHydrated() {
  return useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  )
}

/**
 * One button in the top bar, light against dark.
 *
 * The app still follows the OS until someone presses this; the button is the explicit
 * override, so it only needs the two end states rather than a three-way segmented control.
 */
export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme()
  const hydrated = useHydrated()
  const isDark = hydrated && resolvedTheme === 'dark'

  return (
    <button
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      className="text-muted-foreground hover:bg-accent hover:text-foreground focus-visible:ring-ring grid size-10 cursor-pointer place-items-center rounded-lg transition-colors focus-visible:ring-2 focus-visible:outline-none"
    >
      {/* Before hydration the resolved theme is unknown, so render the moon either way
          and let the swap happen once on the client — no mismatched markup. */}
      {isDark ? <Sun className="size-5" aria-hidden="true" /> : <Moon className="size-5" aria-hidden="true" />}
    </button>
  )
}
