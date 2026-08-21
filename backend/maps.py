"""Map imagery for reports, behind a single switch.

Everything map-related resolves through here so the provider is one decision rather than a
choice scattered across the report generator and the dashboard.

Google Static Maps is used when ``GOOGLE_MAPS_API_KEY`` is set. Without a key there is no
map — the caller falls back to listing the locations in text. That is deliberate: the report
must still generate for someone who has not enabled billing yet, and OpenStreetMap's tile
policy forbids the kind of automated commercial image generation a client report at volume
would amount to.
"""
import logging
import os

logger = logging.getLogger(__name__)

STATIC_MAPS_URL = "https://maps.googleapis.com/maps/api/staticmap"


def api_key() -> str:
    return os.getenv("GOOGLE_MAPS_API_KEY", "").strip()


def is_enabled() -> bool:
    return bool(api_key())


def static_map_url(points: list[dict], width: int = 640, height: int = 360) -> str | None:
    """URL for an image pinning every point, or None when maps are not configured.

    ``points`` are dicts with ``latitude``, ``longitude`` and an optional ``online`` flag.
    No centre or zoom is given: with markers present Google frames them itself, which is
    what you want when a client's screens are spread across a city.
    """
    key = api_key()
    if not key:
        return None

    located = [
        p for p in points
        if p.get("latitude") is not None and p.get("longitude") is not None
    ]
    if not located:
        return None

    params = [
        f"size={width}x{height}",
        "scale=2",  # retina, so the pins are not mushy when printed
        "maptype=roadmap",
    ]
    # Online and offline are separate marker groups so a client can see at a glance that
    # every screen they paid for was actually reporting in.
    for colour, wanted in (("0x16a34a", True), ("0x64748b", False)):
        group = [p for p in located if bool(p.get("online")) is wanted]
        if not group:
            continue
        pins = "|".join(f"{p['latitude']:.6f},{p['longitude']:.6f}" for p in group)
        params.append(f"markers=color:{colour}%7C{pins}")

    params.append(f"key={key}")
    return f"{STATIC_MAPS_URL}?{'&'.join(params)}"


def fetch_static_map(points: list[dict], width: int = 640, height: int = 360) -> bytes | None:
    """The map image itself, or None if unavailable.

    A report must never fail because a map could not be drawn, so every error here is
    swallowed and reported as "no image" — the caller then prints the location list instead.
    """
    url = static_map_url(points, width, height)
    if not url:
        return None
    try:
        import requests

        response = requests.get(url, timeout=10)
        if response.status_code != 200 or not response.content:
            logger.warning("Static map request failed: HTTP %s", response.status_code)
            return None
        return response.content
    except Exception as exc:  # noqa: BLE001 - a missing map must not break a client report
        logger.warning("Static map could not be fetched: %s", exc)
        return None
