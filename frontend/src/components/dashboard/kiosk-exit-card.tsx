'use client'

import { KeyRound, Hand, Gamepad2 } from 'lucide-react'
import type { Screen } from '@/lib/types'

/**
 * How to get out of kiosk on this screen, and the code that does it.
 *
 * A provisioned panel swallows Home and Back — that is the point of kiosk, and it is also how
 * an installer ends up stranded in front of a television with no way into settings. The way
 * out already existed; nothing told anyone what it was, so the only move people found was a
 * factory reset, which unpairs the screen and loses its playlist.
 *
 * The PIN is shown rather than hidden. Secrecy is not what protects a screen here — physical
 * access to it is — and a code the operator cannot see is a code that ends up on a sticky
 * note taped to the bezel.
 */
export function KioskExitCard({ screen }: { screen: Screen }) {
  const pin = screen.effective_maintenance_pin || screen.maintenance_pin
  const isOwnPin = Boolean((screen.maintenance_pin || '').trim())

  return (
    <section className="ring-hairline rounded-2xl p-4 ring-1 sm:p-5">
      <div className="flex items-start gap-3">
        <span className="bg-primary/10 text-primary dark:text-brand grid size-9 shrink-0 place-items-center rounded-lg">
          <KeyRound className="size-4" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="text-foreground font-semibold">Getting into this screen</h2>
          <p className="text-muted-foreground mt-1 text-sm">
            A signage screen blocks Home and Back on purpose, so an advert cannot be closed by
            a passer-by. Use one of these to reach settings.
          </p>

          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div className="bg-secondary/40 rounded-xl p-3">
              <p className="text-foreground flex items-center gap-1.5 text-sm font-medium">
                <Hand className="size-3.5" aria-hidden="true" /> Touch screen
              </p>
              <p className="text-muted-foreground mt-1 text-sm">
                Tap any <span className="text-foreground">corner 7 times</span> within 3 seconds.
              </p>
            </div>
            <div className="bg-secondary/40 rounded-xl p-3">
              <p className="text-foreground flex items-center gap-1.5 text-sm font-medium">
                <Gamepad2 className="size-3.5" aria-hidden="true" /> With a remote
              </p>
              <p className="text-muted-foreground mt-1 text-sm">
                Press <span className="text-foreground">Up, Up, Down, Down, OK</span>.
              </p>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="text-muted-foreground text-sm">Then enter</span>
            {pin ? (
              <code className="bg-primary/10 text-primary dark:text-brand rounded-lg px-3 py-1 text-lg font-semibold tracking-[0.3em]">
                {pin}
              </code>
            ) : (
              <span className="text-sm font-medium text-amber-600 dark:text-amber-400">
                no PIN set — ask your platform administrator
              </span>
            )}
            {pin && !isOwnPin && (
              <span className="text-muted-foreground/70 text-xs">
                (set by your platform administrator for all screens)
              </span>
            )}
          </div>

          <p className="text-muted-foreground/70 mt-3 text-xs">
            Works with no internet: the screen remembers this code, which is exactly when you
            are most likely to need it. Set a different one for this screen under Settings.
          </p>
        </div>
      </div>
    </section>
  )
}
