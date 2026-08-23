'use client'

import { useEffect, useMemo, useRef } from 'react'
import { MapPin } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

export type MapPoint = {
  id: number
  name: string
  location?: string | null
  latitude?: number | null
  longitude?: number | null
  online?: boolean
  /** Optional line under the name in the popup, e.g. "5,210 plays". */
  detail?: string
}

/**
 * Several places on one map, drawn with Leaflet over OpenStreetMap tiles.
 *
 * Google's keyless embed can only ever show one pin, and a campaign map has to show every
 * screen at once. Leaflet does that with no key and no billing; each pin still links out
 * to Google Maps for the place itself.
 */
function LeafletMap({ points, height }: { points: MapPoint[]; height: number }) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<import('leaflet').Map | null>(null)

  // Keyed on the pins' values rather than the array identity, so a parent re-render that
  // produces an equal list does not tear the map down and undo the user's pan.
  const key = JSON.stringify(points.map((p) => [p.id, p.latitude, p.longitude, p.online, p.detail]))

  useEffect(() => {
    let cancelled = false
    let created: import('leaflet').Map | null = null

    // Imported here rather than at module scope: Leaflet touches window on import, which
    // breaks the server render of every page that shows a map.
    import('leaflet').then((L) => {
      if (cancelled || !container.current || map.current) return

      created = L.map(container.current, { scrollWheelZoom: false, attributionControl: true })
      map.current = created
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap',
      }).addTo(created)

      const bounds: [number, number][] = []
      for (const point of points) {
        if (point.latitude == null || point.longitude == null) continue
        const colour = point.online ? '#16a34a' : '#64748b'
        const marker = L.marker([point.latitude, point.longitude], {
          title: point.name,
          icon: L.divIcon({
            className: '',
            html: `<div style="width:18px;height:18px;border-radius:9999px;background:${colour};border:3px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4)"></div>`,
            iconSize: [18, 18],
            iconAnchor: [9, 9],
          }),
        }).addTo(created)
        marker.bindPopup(
          `<div style="font:500 13px system-ui;min-width:150px">
             <div style="font-weight:600">${point.name}</div>
             ${point.location ? `<div style="color:#64748b">${point.location}</div>` : ''}
             ${point.detail ? `<div style="margin-top:3px">${point.detail}</div>` : ''}
             <div style="margin-top:3px;color:${colour}">${point.online ? 'Online' : 'Offline'}</div>
             <a href="https://www.google.com/maps/search/?api=1&query=${point.latitude},${point.longitude}"
                target="_blank" rel="noreferrer" style="display:inline-block;margin-top:5px">Open in Google Maps</a>
           </div>`,
        )
        bounds.push([point.latitude, point.longitude])
      }

      if (bounds.length === 1) created.setView(bounds[0], 15)
      else if (bounds.length) created.fitBounds(bounds, { padding: [40, 40] })
    })

    return () => {
      cancelled = true
      created?.remove()
      if (map.current === created) map.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- keyed on values, not reference
  }, [key])

  return (
    <div className="border-hairline relative overflow-hidden rounded-xl border" style={{ height }}>
      <div ref={container} className="size-full" />
    </div>
  )
}

function NoLocations({ points }: { points: MapPoint[] }) {
  const named = [...new Set(points.map((p) => p.location).filter(Boolean))] as string[]
  return (
    <div className="border-hairline bg-muted/30 rounded-xl border border-dashed p-6 text-center">
      <MapPin className="text-muted-foreground/50 mx-auto size-6" aria-hidden="true" />
      <p className="text-foreground mt-2 text-sm font-medium">No locations pinned yet</p>
      <p className="text-muted-foreground mt-1 text-sm">
        Open a screen&apos;s Settings and paste its Google Maps link to put it on the map.
      </p>
      {named.length > 0 && (
        <div className="mt-3 flex flex-wrap justify-center gap-2">
          {named.map((place) => (
            <Badge key={place} variant="secondary">
              <MapPin className="size-3" /> {place.length > 40 ? `${place.slice(0, 40)}…` : place}
            </Badge>
          ))}
        </div>
      )}
    </div>
  )
}

/**
 * Where a set of screens physically are.
 *
 * Pins are tinted by whether the screen is reporting in, so a client-facing map doubles as
 * a health check: a grey pin is a screen that was sold but is not answering.
 */
export function ScreenMap({ points, height = 320 }: { points: MapPoint[]; height?: number }) {
  const located = useMemo(
    () => points.filter((p) => p.latitude != null && p.longitude != null),
    [points],
  )

  if (!located.length) return <NoLocations points={points} />
  // Every case goes through Leaflet, including a single pin -- LeafletMap already handles
  // that with setView.
  //
  // A single place used to render Google's keyless embed
  // (maps.google.com/maps?q=..&output=embed). Google now 301s that to
  // /maps/embed?origin=mfe&pb=.. which answers 404 AND sets X-Frame-Options: SAMEORIGIN,
  // so the iframe was a permanently grey box -- and only ever on the one-pin path, which
  // is exactly what an operator sees with their first screen.
  return <LeafletMap points={located} height={height} />
}
