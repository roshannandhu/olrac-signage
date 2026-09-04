export function relativeTime(value: string | null | undefined): string {
  if (!value) return 'Never'
  const timestamp = new Date(value).getTime()
  if (Number.isNaN(timestamp)) return 'Unknown'
  const seconds = Math.round((timestamp - Date.now()) / 1000)
  const formatter = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })
  const ranges: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ['year', 60 * 60 * 24 * 365],
    ['month', 60 * 60 * 24 * 30],
    ['day', 60 * 60 * 24],
    ['hour', 60 * 60],
    ['minute', 60],
  ]
  for (const [unit, divisor] of ranges) {
    if (Math.abs(seconds) >= divisor) return formatter.format(Math.round(seconds / divisor), unit)
  }
  return 'just now'
}

export function loopDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const remainder = seconds % 60
  return remainder ? `${minutes}m ${remainder}s` : `${minutes}m`
}

export function storageUsedGb(value: string | null | undefined): number {
  if (!value) return 0
  const parsed = Number.parseFloat(value)
  return Number.isFinite(parsed) ? parsed : 0
}

export function dateTimeLocal(value: string | null | undefined): string {
  return value ? value.slice(0, 16) : ''
}

/**
 * A value for `<input type="date">`, in the operator's own timezone.
 *
 * `toISOString().slice(0, 10)` is the obvious way to write this and it is wrong: it takes
 * the UTC date off an instant, while the input renders and the operator reads a LOCAL one.
 * In IST that is a day out in two different ways -- `new Date()` before 05:30 gives
 * yesterday, and adding a plan's duration to a local midnight lands the previous UTC day,
 * so picking a 30-day plan sold 29 days. Every plan-based booking was short by one.
 *
 * `en-CA` is the locale whose short date format is already YYYY-MM-DD, so this needs no
 * padding of its own.
 */
export function dateInput(value: Date | string | number): string {
  const date = value instanceof Date ? value : new Date(value)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString('en-CA')
}

/** Add whole days to a `<input type="date">` value, staying on local calendar days. */
export function addDays(value: string, days: number): string {
  const date = new Date(`${value}T00:00:00`)
  if (Number.isNaN(date.getTime())) return value
  date.setDate(date.getDate() + days)
  return dateInput(date)
}

/** A stored instant as a readable day. Timestamps arrive tz-aware, so this is local. */
export function asDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const date = new Date(iso)
  return Number.isNaN(date.getTime())
    ? '—'
    : date.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

export function expiryLabel(value: string | null): string | null {
  if (!value) return null
  const days = Math.ceil((new Date(value).getTime() - Date.now()) / 86_400_000)
  if (days < 0) return 'Expired'
  if (days === 0) return 'Expires today'
  if (days === 1) return 'Expires tomorrow'
  return `Expires in ${days} days`
}

/** Clip length as m:ss, the way a player scrubber shows it. */
export function clipDuration(ms: number | null | undefined): string | null {
  if (!ms || ms <= 0) return null
  const total = Math.round(ms / 1000)
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

/**
 * "portrait" / "landscape" for an asset, read off its largest rendition.
 *
 * Returns null when nothing has been transcoded yet — better to omit the word than to
 * guess landscape and mislabel a portrait advert.
 */
export function assetOrientation(renditions?: { width: number; height: number }[]): string | null {
  const largest = renditions?.slice().sort((a, b) => b.width * b.height - a.width * a.height)[0]
  if (!largest?.width || !largest?.height) return null
  return largest.height > largest.width ? 'portrait' : 'landscape'
}

/** Human file size. Whole numbers above 10 so a table of sizes stays aligned. */
export function formatBytes(bytes: number | null | undefined): string {
  if (!bytes) return '—'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  const value = bytes / 1024 ** exponent
  return `${value.toFixed(value >= 10 || exponent === 0 ? 0 : 1)} ${units[exponent]}`
}

/**
 * Paise as rupees. Money is stored in the smallest unit so it never touches a float.
 *
 * One copy because there were six, in ad-bookings, campaigns, plans, clients, content and
 * the client-ad modal, and they had already drifted — some grouped with en-IN lakh
 * separators and some did not, so the same booking read as ₹2,50,000 on one page and
 * ₹250,000 on the next.
 */
export function rupees(paise: number | null | undefined): string {
  return `₹${((paise ?? 0) / 100).toLocaleString('en-IN')}`
}

/**
 * Whether a booking is scheduled, running or finished.
 *
 * Reads `effective_ends_at`, which counts extensions and per-location windows. There were
 * two copies of this and they disagreed: the bookings tab compared against the SOLD
 * `ends_at`, so a campaign the client had just paid to extend showed as "Ended" on the
 * page where you extend it, while the campaigns list showed the same booking as Running.
 */
export function bookingState(placement: {
  starts_at: string
  ends_at: string
  effective_ends_at?: string | null
}): { label: 'Scheduled' | 'Running' | 'Ended'; tone: 'success' | 'warning' | 'outline' } {
  const now = Date.now()
  const end = Date.parse(placement.effective_ends_at || placement.ends_at)
  if (Date.parse(placement.starts_at) > now) return { label: 'Scheduled', tone: 'warning' }
  if (end < now) return { label: 'Ended', tone: 'outline' }
  return { label: 'Running', tone: 'success' }
}
