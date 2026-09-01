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
from functools import lru_cache
from io import BytesIO

logger = logging.getLogger(__name__)

STATIC_MAPS_URL = "https://maps.googleapis.com/maps/api/staticmap"


def api_key() -> str:
    return os.getenv("GOOGLE_MAPS_API_KEY", "").strip()


def is_enabled() -> bool:
    """Whether a map can be produced at all.

    Always true now: without a Google key the report renders its own image from the same
    OpenStreetMap tiles the dashboard's screen map already uses, so a tenant is never left
    with a blank panel because billing was not set up.
    """
    return True


def google_configured() -> bool:
    """Google specifically, which is preferred when a key exists -- better cartography and
    no shared-tile-server etiquette to observe."""
    return bool(api_key())


# The dashboard's screen-map uses this exact endpoint (see components/dashboard/screen-map).
# Using the same source keeps the printed map and the on-screen one recognisably the same
# place.
#
# OSM asks for a User-Agent that identifies the application and for light, cached use. A
# report draws a handful of tiles and the cache below means a second report of the same
# area draws none, which is well inside that. Attribution is stamped onto the image, which
# their terms require and which a client-facing document should carry anyway.
OSM_TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
OSM_USER_AGENT = "OlracSignage/1.0 (campaign reports; +https://github.com/roshannandhu/olrac-signage)"
TILE_PX = 256


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


def _project(latitude: float, longitude: float, zoom: int) -> tuple[float, float]:
    """Web-Mercator pixel coordinates at a zoom level. The standard slippy-map maths."""
    import math

    scale = TILE_PX * (2 ** zoom)
    x = (longitude + 180.0) / 360.0 * scale
    sin_lat = math.sin(math.radians(latitude))
    # Clamped: the projection is undefined at the poles and a screen with a corrupt
    # latitude would otherwise raise inside a report.
    sin_lat = max(-0.9999, min(0.9999, sin_lat))
    y = (0.5 - math.log((1 + sin_lat) / (1 - sin_lat)) / (4 * math.pi)) * scale
    return x, y


def _choose_zoom(located: list[dict], width: int, height: int) -> int:
    """The closest zoom that still fits every pin, with a margin so none sits on the edge."""
    lats = [p["latitude"] for p in located]
    lons = [p["longitude"] for p in located]
    if len(located) == 1 or (max(lats) == min(lats) and max(lons) == min(lons)):
        # One screen, or several at the same address: framing has nothing to fit, so pick a
        # neighbourhood-level zoom rather than the whole world.
        return 14

    for zoom in range(17, 1, -1):
        top_left_x, top_left_y = _project(max(lats), min(lons), zoom)
        bottom_right_x, bottom_right_y = _project(min(lats), max(lons), zoom)
        if (bottom_right_x - top_left_x) < width * 0.82 and (bottom_right_y - top_left_y) < height * 0.82:
            return zoom
    return 2


@lru_cache(maxsize=512)
def _tile(zoom: int, x: int, y: int) -> bytes | None:
    """One map tile. Cached, so a second report of the same city fetches nothing."""
    import urllib.request

    url = OSM_TILES.format(z=zoom, x=x, y=y)
    try:
        request = urllib.request.Request(url, headers={"User-Agent": OSM_USER_AGENT})
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status != 200:
                logger.warning("Tile %s returned HTTP %s", url, response.status)
                return None
            return response.read() or None
    except Exception as exc:  # noqa: BLE001 - a missing tile degrades the map, nothing more
        logger.warning("Tile %s could not be fetched: %s", url, exc)
        return None


def render_osm_map(points: list[dict], width: int = 640, height: int = 360) -> bytes | None:
    """Draw the map ourselves, from the tiles the dashboard already uses.

    Returns PNG bytes, or None if nothing could be drawn. Never raises: a report must still
    generate when the tile server is unreachable.
    """
    located = [p for p in points if p.get("latitude") is not None and p.get("longitude") is not None]
    if not located:
        return None

    try:
        from PIL import Image, ImageDraw
    except ImportError:  # pragma: no cover - Pillow ships with ReportLab
        logger.warning("Pillow is unavailable, so no map can be drawn")
        return None

    try:
        import math

        zoom = _choose_zoom(located, width, height)
        centre_lat = (max(p["latitude"] for p in located) + min(p["latitude"] for p in located)) / 2
        centre_lon = (max(p["longitude"] for p in located) + min(p["longitude"] for p in located)) / 2
        centre_x, centre_y = _project(centre_lat, centre_lon, zoom)

        # Pixel coordinates of the image's top-left corner in the world projection.
        origin_x = centre_x - width / 2
        origin_y = centre_y - height / 2

        canvas = Image.new("RGB", (width, height), (233, 233, 226))
        max_tile = 2 ** zoom
        first_tx, last_tx = math.floor(origin_x / TILE_PX), math.floor((origin_x + width) / TILE_PX)
        first_ty, last_ty = math.floor(origin_y / TILE_PX), math.floor((origin_y + height) / TILE_PX)

        for tile_x in range(first_tx, last_tx + 1):
            for tile_y in range(first_ty, last_ty + 1):
                if not (0 <= tile_y < max_tile):
                    continue
                # Wrapped, so a fleet either side of the date line still draws.
                raw = _tile(zoom, tile_x % max_tile, tile_y)
                if not raw:
                    continue
                try:
                    tile = Image.open(BytesIO(raw)).convert("RGB")
                except Exception:  # noqa: BLE001 - one bad tile, not a failed report
                    continue
                canvas.paste(tile, (int(tile_x * TILE_PX - origin_x), int(tile_y * TILE_PX - origin_y)))

        draw = ImageDraw.Draw(canvas)
        for point in located:
            px, py = _project(point["latitude"], point["longitude"], zoom)
            x, y = px - origin_x, py - origin_y
            if not (-20 <= x <= width + 20 and -20 <= y <= height + 20):
                continue
            # Green for a screen that is reporting in, slate for one that is not -- the same
            # distinction the Google markers drew, so a client can see at a glance that
            # every screen they paid for was actually live.
            fill = (22, 163, 74) if point.get("online") else (100, 116, 139)
            draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=fill, outline=(255, 255, 255), width=2)
            draw.polygon([(x - 4, y + 5), (x + 4, y + 5), (x, y + 13)], fill=fill)

        # Required by the tile terms, and a client-facing document should carry it anyway.
        note = "(C) OpenStreetMap contributors"
        draw.rectangle((width - 168, height - 15, width, height), fill=(255, 255, 255))
        draw.text((width - 164, height - 12), note, fill=(80, 80, 80))

        buffer = BytesIO()
        canvas.save(buffer, format="PNG")
        return buffer.getvalue()
    except Exception as exc:  # noqa: BLE001 - a map must never break a client report
        logger.warning("Map could not be rendered: %s", exc)
        return None


def fetch_static_map(points: list[dict], width: int = 640, height: int = 360) -> bytes | None:
    """The map image itself, or None if unavailable.

    A report must never fail because a map could not be drawn, so every error here is
    swallowed and reported as "no image" — the caller then prints the location list instead.
    """
    url = static_map_url(points, width, height)
    if not url:
        # No Google key. Draw it ourselves from the same OpenStreetMap tiles the dashboard
        # uses, rather than leaving the client's report with an empty panel and a note about
        # billing they neither caused nor can fix.
        return render_osm_map(points, width, height)
    try:
        # urllib rather than requests, which was imported here and listed in no
        # requirements file. Because every error below is swallowed, the missing package
        # did not crash anything -- it just meant the map was silently absent from every
        # client report in any environment that had not hand-installed it. The Razorpay
        # provider already calls out over urllib; this matches it and drops the
        # undeclared dependency instead of adding it.
        import urllib.request

        with urllib.request.urlopen(url, timeout=10) as response:
            if response.status != 200:
                logger.warning("Static map request failed: HTTP %s", response.status)
                return None
            content = response.read()
        if not content:
            logger.warning("Static map request returned an empty body")
            return None
        return content
    except Exception as exc:  # noqa: BLE001 - a missing map must not break a client report
        logger.warning("Static map could not be fetched: %s", exc)
        return None
