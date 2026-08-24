'use client'

import { useEffect, useRef, useState } from 'react'
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
 * Does this look like a link rather than the name of a place?
 *
 * Deliberately loose. It only decides whether to *try* resolving, and the API is what
 * actually rules on the host — being generous here means a link still resolves when it
 * arrives without its scheme, which is what copying from a phone produces. A place is
 * never named like this, so nothing an operator types by hand is diverted by mistake.
 */
const looksLikeLink = (text: string) =>
  /^(https?:\/\/|www\.|maps\.|share\.google|goo\.gl|g\.co)\S*$/i.test(text.trim())

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
  // The last link handed to the API. Without it a link that fails is retried on every
  // render, hammering the endpoint with a request already known to be refused.
  const attempted = useRef('')

  /**
   * @param raw the link to resolve, when it is not yet in state.
   */
  const resolve = async (raw?: string) => {
    const trimmed = (raw ?? link).trim()
    if (!trimmed || busy) return
    attempted.current = trimmed
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

  // Anything that looks like a link resolves itself, whichever way it got into the box --
  // pasted, typed, autofilled, or dropped in. Setting a location is done once per screen
  // and across a whole fleet, so pressing a button afterwards is a step repeated for
  // every TV to say something the link already said.
  //
  // Debounced because this also fires per keystroke while a link is being typed; the
  // delay lets the value settle instead of resolving a dozen prefixes of it.
  useEffect(() => {
    const trimmed = link.trim()
    if (!trimmed || busy || trimmed === attempted.current || !looksLikeLink(trimmed)) return
    const timer = setTimeout(() => resolve(trimmed), 400)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [link, busy])

  const clear = () => {
    attempted.current = ''
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
            const typed = event.target.value
            // A link dropped in the name box is still a link. Naming a screen
            // "https://share.google/..." is never what was meant, so it is sent to the
            // link box to resolve rather than saved as the place's name.
            if (looksLikeLink(typed)) {
              setLink(typed)
              setError(null)
              return
            }
            setName(typed)
            // Renaming keeps the pin; only a new link or Clear moves it.
            onChange({ ...value, location: typed })
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
            // No paste handler: the effect above already covers pasting, and every other
            // way a link arrives, from one code path rather than two racing each other.
            onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); resolve() } }}
            placeholder="Paste Google Maps link"
            disabled={busy}
            className="pl-9"
            autoComplete="off"
          />
        </div>
        {/* Wrapped, not passed directly: resolve takes an optional link, and onClick would
            hand it the mouse event to trim. */}
        <Button type="button" variant="outline" onClick={() => resolve()} disabled={!link.trim() || busy}>
          {busy ? <Loader2 className="size-4 animate-spin" /> : 'Pin'}
        </Button>
      </div>

      {busy ? (
        <p className="text-muted-foreground flex items-center gap-1.5 text-sm">
          <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
          Reading that link...
        </p>
      ) : error ? (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      ) : pinned ? (
        <p className="flex items-center gap-1.5 text-sm text-green-700 dark:text-green-400">
          <Check className="size-3.5" aria-hidden="true" />
          Pinned at {value.latitude!.toFixed(4)}, {value.longitude!.toFixed(4)}
        </p>
      ) : (
        <p className="text-muted-foreground text-xs">
          In Google Maps, find the place → <strong className="font-medium">Share</strong> →{' '}
          <strong className="font-medium">Copy link</strong>, then paste it above and it pins
          itself. Short
          share.google links work too.
        </p>
      )}
    </div>
  )
}
