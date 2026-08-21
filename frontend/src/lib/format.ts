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
