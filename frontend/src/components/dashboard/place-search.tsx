'use client'

import { useState } from 'react'
import { Check, Link2, Loader2, MapPin, X } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'

export type Place = {
  location: string
  latitude: number | null
  longitude: number | null
  place_id: string | null
}

/**
 * Set a screen's location by pasting the Google Maps link for it.
 *
 * This replaces a search box that needed the Places API — which needs a key, which needs a
 * billing account. Every Google Maps URL already carries either the coordinate or the
 * place name, so pasting the link operators already share is both free and closer to how
 * they actually work: find the shop in Google Maps, Share, paste.
 */
export function PlaceSearch({ value, onChange }: { value: Place; onChange: (place: Place) => void }) {
  const [link, setLink] = useState('')
  const [name, setName] = useState(value.location)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const pinned = value.latitude != null && value.longitude != null

  const resolve = async () => {
    const trimmed = link.trim()
    if (!trimmed) return
    setBusy(true)
    setError(null)
    try {
      const found = await api.resolveLocationLink(trimmed)
      // Keep a name the operator already typed; otherwise take Google's.
      const label = name.trim() || found.name || `${found.latitude.toFixed(4)}, ${found.longitude.toFixed(4)}`
      setName(label)
      onChange({
        location: label,
        latitude: found.latitude,
        longitude: found.longitude,
        place_id: null,
      })
      setLink('')
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : 'That link could not be read.')
    } finally {
      setBusy(false)
    }
  }

  const clear = () => {
    setName('')
    setLink('')
    setError(null)
    onChange({ location: '', latitude: null, longitude: null, place_id: null })
  }

  return (
    <div className="space-y-2">
      <div className="relative">
        <MapPin className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2" aria-hidden="true" />
        <Input
          id="screen-location"
          value={name}
          onChange={(event) => {
            setName(event.target.value)
            // Renaming keeps the pin; only a new link or Clear moves it.
            onChange({ ...value, location: event.target.value })
          }}
          placeholder="Name of this place, e.g. Lulu Mall — Main Entrance"
          className="pr-9 pl-9"
          autoComplete="off"
        />
        {name && (
          <button
            type="button"
            onClick={clear}
            aria-label="Clear location"
            className="text-muted-foreground hover:text-foreground absolute top-1/2 right-2 grid size-6 -translate-y-1/2 cursor-pointer place-items-center rounded"
          >
            <X className="size-4" />
          </button>
        )}
      </div>

      <div className="flex gap-2">
        <div className="relative flex-1">
          <Link2 className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2" aria-hidden="true" />
          <Input
            value={link}
            onChange={(event) => { setLink(event.target.value); setError(null) }}
            onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); resolve() } }}
            placeholder="Paste Google Maps link"
            className="pl-9"
            autoComplete="off"
          />
        </div>
        <Button type="button" variant="outline" onClick={resolve} disabled={!link.trim() || busy}>
          {busy ? <Loader2 className="size-4 animate-spin" /> : 'Pin'}
        </Button>
      </div>

      {error ? (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      ) : pinned ? (
        <p className="flex items-center gap-1.5 text-sm text-green-700 dark:text-green-400">
          <Check className="size-3.5" aria-hidden="true" />
          Pinned at {value.latitude!.toFixed(4)}, {value.longitude!.toFixed(4)}
        </p>
      ) : (
        <p className="text-muted-foreground text-xs">
          In Google Maps, find the place → <strong className="font-medium">Share</strong> →{' '}
          <strong className="font-medium">Copy link</strong>, then paste it above. Short
          share.google links work too.
        </p>
      )}
    </div>
  )
}
