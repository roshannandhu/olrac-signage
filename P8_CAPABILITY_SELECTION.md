# P8 — Per-TV capability detection and rendition selection

**Why this exists:** P2 built half a feature. The worker generates 1080p/720p/540p/360p
renditions and the API returns them, but the Android `ContentDto` has **no renditions
field at all** — the player downloads `content.file_url`, the original upload. A budget
1 GB-RAM 1080p panel therefore downloads and tries to decode the original 4K HEVC file.
Spec §8 and §9 exist specifically to prevent this.

Three pieces are missing: the TV never reports what it can play, the backend has nowhere
to store that, and nothing chooses a rendition.

---

## 1. Device reports its capabilities (Android)

New `DeviceCapabilities.kt`. Collect once at startup and whenever the app version changes;
send with the existing heartbeat rather than adding a new endpoint.

| Field | Source |
|---|---|
| `screen_width`, `screen_height` | `DisplayMetrics` / `Display.getRealMetrics` |
| `refresh_rate` | `Display.getRefreshRate()` |
| `orientation` | derived from width vs height |
| `total_ram_mb`, `available_ram_mb` | `ActivityManager.MemoryInfo` |
| `total_storage_mb`, `free_storage_mb` | `StatFs` on `filesDir` |
| `supported_video_codecs` | `MediaCodecList(REGULAR_CODECS)` — decoders only |
| `max_decode_width`, `max_decode_height` | `CodecCapabilities.getVideoCapabilities()` for H.264 |
| `manufacturer`, `model`, `android_version`, `sdk_int` | `Build` |
| `network_type` | `ConnectivityManager` (wifi / ethernet / other) |
| `timezone` | `TimeZone.getDefault().id` |

Report **decoders**, not encoders — `MediaCodecList` includes both and only decode matters.
Cache the result in `SharedPreferences`; probing `MediaCodecList` on every heartbeat is
wasteful on a slow TV.

## 2. Backend stores the profile

Add these columns to `Screen` (all nullable — an unreported screen must still work), plus
an Alembic migration. Extend `HeartbeatRequest` to accept them, ignoring unknown fields so
an older APK keeps working.

Do **not** create a separate `capabilities` table for a one-to-one relationship.

## 3. Backend picks the rendition

New `backend/media_selection.py`, pure and unit-testable:

```
select_rendition(content, screen) -> MediaRendition | None
```

Rules, in order:
1. No renditions ready → return None, fall back to the original (current behaviour).
2. Screen never reported capabilities → return the **720p** rendition. A safe default beats
   guessing; do not send 4K to an unknown device.
3. Drop any rendition whose codec the screen does not list as supported.
4. Drop any rendition exceeding `max_decode_width`/`max_decode_height`.
5. Of what remains, pick the **largest that fits the panel** — never upscale beyond
   `screen_width`/`screen_height`, and never exceed a 1080p rendition on a 1080p panel.
6. If `total_ram_mb` < 1536, cap at 720p regardless of panel size. Budget TVs report
   1080p panels they cannot smoothly decode at full bitrate.
7. Portrait panels keep portrait renditions. Never rotate or crop to make one fit.

`sync_tv` sets `item.content.file_url` (and `sha256`, `file_size_bytes`) to the chosen
rendition's values, so the player's existing integrity check keeps working unchanged.

**This is the key design decision:** substitute server-side rather than teaching the player
to choose. The player already downloads `file_url`, verifies `sha256`, and caches it — none
of that changes, so this cannot break offline playback or the atomic playlist switch.

## 4. Dashboard

On the screen detail page show the reported profile (resolution, RAM, free storage,
codecs, Android version) and, per playlist item, which rendition that screen will receive.
An operator must be able to answer "why is this TV getting 540p?" without reading logs.

---

## Definition of done

- A 4K HEVC upload plays correctly on a 1 GB-RAM 1080p panel, having downloaded the
  720p H.264 rendition and **not** the original.
- A portrait phone video stays portrait on a portrait panel, uncropped.
- A screen that has never reported capabilities still plays (720p default), proving the
  change cannot brick an existing fleet.
- A screen whose codec list excludes HEVC never receives an HEVC file.
- Offline playback and power-cut recovery still pass on hardware — this touches the sync
  payload, so both must be re-verified.

## Tests

`tests/test_media_selection.py` — a **script** with its own throwaway Postgres database, a
`__main__` block, and no `test_*` function. Read `tests/conftest.py` and `pytest.ini`
first. Cover: no capabilities → 720p; HEVC excluded when unsupported; 1 GB RAM capped at
720p; portrait preserved; no renditions → original; and that `sha256`/`file_size_bytes` are
swapped to match the chosen rendition, or the player will reject the download.

Then run the full suite with Redis up and down, and paste both results.
