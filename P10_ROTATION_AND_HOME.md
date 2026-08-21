# P10 — Display rotation, and an operations home page

Two pieces of work. Rotation is the higher priority: it is the only outstanding item that
makes content display *wrong* rather than merely inconvenient.

Neither needs new data collection. Almost everything required is already captured and
sitting unused.

---

# Part A — Display rotation

## What already exists

| Piece | Where | State |
|---|---|---|
| TV reports its physical orientation | `DeviceCapabilities.kt:117` (`screenWidth > screenHeight ? 0 : 90`) | ✅ reported every heartbeat |
| `Screen.orientation` column, validated 0/90/180/270 | `backend/models.py` | ✅ stored |
| Content native orientation | `MediaRendition.rotation`, from ffprobe | ✅ captured |
| Player applies rotation | `ui/PlayerScreen.kt` | ❌ **nothing, anywhere** |

A portrait-mounted TV therefore plays landscape video sideways. The plumbing is done; the
last step was never built.

## The model — three layers, in precedence order

1. **Per-item override** (`PlaylistItem.rotation`, new, nullable) — wins when set
2. **Screen override** (`Screen.orientation`, existing) — set by an operator when the
   auto-detected value is wrong
3. **Auto-detected** from the panel — the default

Resolve to a single value in one place and hand the player a number.

## Backend

- Add `rotation` (nullable int, 0/90/180/270) to `PlaylistItem`, plus a migration and the
  matching schema/response fields.
- Add `Screen.orientation_source` (`"auto"` | `"manual"`). Without it an operator's manual
  override is silently overwritten by the next heartbeat — the bug that will otherwise be
  reported as "rotation keeps resetting itself".
- `sync_tv` returns an effective `rotation` per playlist item, resolved by the precedence
  above, so the player does no reasoning.

## Player

- Read `rotation` on `PlaylistItemEntity` (Room migration, nullable) and apply it with
  `Modifier.graphicsLayer(rotationZ = …)` on the surface container.
- **Swap the container's width and height for 90/270**, or a rotated video renders
  letterboxed inside the wrong box.
- **Do not double-rotate.** Media3 already honours the `rotate` metadata tag that phone
  footage carries. Apply only the *difference* between content orientation and the
  resolved target, not both.
- Apply the same rotation to images (Coil) and to the idle/error screens, or the fallback
  states appear sideways on a portrait panel.

## Dashboard

- Screen detail: show detected orientation, with an override dropdown
  (Auto / 0° / 90° / 180° / 270°) that sets `orientation_source = "manual"`.
- Playlist builder: a small rotate control per item, defaulting to "Follow screen".

## Definition of done

- Landscape video on a portrait-mounted TV fills the screen the right way up.
- Portrait video on a landscape TV is pillarboxed, not stretched or cropped.
- A manual override survives heartbeats and reboots.
- Images and the "waiting for content" screen rotate too.
- A screen with no rotation set behaves exactly as it does today.

---

# Part B — Operations home page

## The problem

The current home shows four counters: screens online, media assets, active playlists,
device storage. That answers *"how much do I have?"*. With 80 TVs the operator's question
is *"what is broken right now and what do I click?"*.

Nobody has ever taken an action because they had four playlists.

## Every panel below uses data that already exists

| Panel | Source | Already there? |
|---|---|---|
| Needs attention | `Screen.status`, `playback_state`, `last_error`, `Content.status='failed'` | ✅ P4 / P2 |
| Fleet strip | same | ✅ |
| On air now | `Screen.current_item_id` → content name | ✅ P4 |
| Today's plays | `play_log_hourly_rollups` | ✅ P5 |

No new collection, no new tables. This is presentation work.

## Layout

```
NEEDS ATTENTION            ← render only when non-empty; never an empty box
  3 screens offline >30min                    [View]
  Lobby TV — codec failure                    [See error]
  "summer-ad.mp4" transcode failed            [Retry]
  Campaign "Summer" ends in 2 days            [Extend]

FLEET   ████████████░░░░   62 playing · 9 idle · 6 offline · 3 error
        every segment clicks through to a filtered screen list

ON AIR NOW                      TODAY
  Coca-Cola      27 screens     1,842 plays   ▁▃▅▇▆▅▇   ↑12% vs yesterday
  Nike           18 screens
  Samsung        12 screens
                                [Upload]  [New playlist]  [Emergency]
```

## Rules

- **Remove** the "media assets" and "active playlists" counters. They are not actionable.
- Every alert row must be **one click from the fix**, not a dead label.
- "Needs attention" disappears entirely when there is nothing wrong. A permanently visible
  empty alert box trains people to ignore the whole panel.
- **"On air now" is the most valuable panel on the page** — it is what a customer rings up
  about. Group by content, count screens, refresh on the existing 30s interval.
- Keep the existing navy tokens and stagger animation. This is a restructure, not a
  reskin.
- Degrade honestly: if the rollup job has not run, show "no data yet", never a zero that
  reads like a real measurement.

## Definition of done

- With every screen healthy, the page is calm and shows no alert block.
- Unplug a TV: it appears under Needs attention within one refresh, and clicking it lands
  on that screen's detail page.
- A failed transcode is visible on the home page and retryable from there.
- "On air now" matches what the screens are actually playing.
- Page renders correctly with zero screens, zero content, and zero play history — the
  first-run state must not be a wall of empty widgets.

---

## Order of work

Rotation first. A sideways advert is worse than no advert, and the customer sees it.
The home page is internal and can follow immediately after.

## Verification

Backend: `pytest tests -q` with Redis up and down.
Frontend: `npx tsc --noEmit`, `npm run lint`, `npm run build` — all three, separately.
`next build` does **not** run ESLint in Next 16; a clean build is not a clean lint.
Android: `gradlew testDevDebugUnitTest assembleDevDebug`, and report the test totals.

Rotation cannot be fully proven without a physical portrait-mounted panel. Say so plainly
rather than implying automated coverage.
