'use client'

import * as React from 'react'

type TransitionClass = string | Record<string, string>

type ViewTransitionProps = {
  children: React.ReactNode
  name?: string
  default?: TransitionClass
  enter?: TransitionClass
  exit?: TransitionClass
  share?: TransitionClass
}

/**
 * React ships <ViewTransition> in the canary build that Next vendors for the App
 * Router, but @types/react (19.2.x) does not declare it yet. This wrapper types
 * it locally and falls back to rendering children untouched if the runtime does
 * not expose it, so a React downgrade degrades to no animation instead of a crash.
 */
const ReactViewTransition = (
  React as unknown as { ViewTransition?: React.ComponentType<ViewTransitionProps> }
).ViewTransition

export function ViewTransition({ children, ...props }: ViewTransitionProps) {
  if (!ReactViewTransition) return <>{children}</>
  return <ReactViewTransition {...props}>{children}</ReactViewTransition>
}
