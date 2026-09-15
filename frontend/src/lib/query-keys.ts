import type { QueryClient } from '@tanstack/react-query'

/**
 * Refresh everything a booking change can affect.
 *
 * There were two copies of this list and they had drifted, which is what every stale-view
 * bug on the ad pages turned out to be:
 *
 *   - the bookings tab did not invalidate `content`, so the page header two inches above
 *     it kept showing the old client and plan after a booking was created or deleted;
 *   - it did not invalidate `plan-options`, so reopening "Change plan" still badged the
 *     previous plan as current and quoted a difference against it;
 *   - the client-ad modal did not invalidate `playlists`, `screens` or `all-placements`,
 *     even though its mutation creates and deletes playlist items -- so the page hosting
 *     it went on saying "Not scheduled on any screen yet" about the screens just assigned,
 *     and the campaigns and invoices pages kept the old rows.
 *
 * One list, called from both. React Query matches by prefix, so these also cover the keyed
 * variants: `['content', id]`, `['placements', contentId]`, `['plan-options', id]`.
 */
export function invalidateBookingViews(queryClient: QueryClient): void {
  const keys = [
    ['content'],
    ['placements'],
    ['all-placements'],
    ['plan-options'],
    ['playlists'],
    // The playback timeline itself, which the builder reads under ['playlist', id] --
    // SINGULAR, and prefix matching does not reach it from ['playlists']. So booking an
    // advert from the library left the loop it was booked into showing the old items: the
    // asset vanished from the library (it is filtered by what the timeline holds) and never
    // appeared on the other side until the page was reloaded by hand.
    ['playlist'],
    ['screens'],
    ['groups'],
    ['clients'],
  ]
  for (const queryKey of keys) queryClient.invalidateQueries({ queryKey })
}
