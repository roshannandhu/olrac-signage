import { redirect } from 'next/navigation'

/**
 * There is no separate overview screen.
 *
 * The old one showed inventory counts ("4 playlists") that nobody acted on. An operator
 * opening the console wants the content library, which is where every task starts, so
 * /dashboard lands there instead of on a wall of statistics.
 */
export default function DashboardIndex() {
  redirect('/dashboard/content')
}
