"""Turn a shared Google Maps link into coordinates.

This exists so setting a screen's location needs no API key and no billing account. People
already share places as links — "share" in the Google Maps app produces exactly what this
parses — and every form of that link carries the coordinates in the URL itself.

Short maps.app.goo.gl / goo.gl/maps links do not, so those are resolved by following the
redirect, which is an ordinary HTTP request rather than a billed API call.
"""
from __future__ import annotations

import logging
import re
import json
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

# Long-form links put the map centre after "@", e.g. /maps/place/Name/@9.9312,76.2673,17z
_AT = re.compile(r"@(-?\d{1,3}\.\d+),(-?\d{1,3}\.\d+)")
# "!3dLAT!4dLNG" is the *place* itself, which is more accurate than the map centre.
_BANG = re.compile(r"!3d(-?\d{1,3}\.\d+)!4d(-?\d{1,3}\.\d+)")
# ?q=LAT,LNG / ?query=LAT,LNG / ?ll=LAT,LNG / ?destination=LAT,LNG
_QUERY_KEYS = ("q", "query", "ll", "center", "destination", "daddr")
_PAIR = re.compile(r"^\s*(-?\d{1,3}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)\s*$")

# share.google is what the Android "Share" sheet now produces, and it is the form
# operators actually paste. It carries no coordinates until the redirect is followed.
SHORT_HOSTS = {"maps.app.goo.gl", "goo.gl", "maps.google.com", "g.co", "share.google"}
ACCEPTED_HOSTS = ("google.com", "goo.gl", "google.co.in", "share.google", "g.co")
TIMEOUT = 8


class MapsLinkError(ValueError):
    """The link could not be turned into a coordinate."""


def _valid(lat: float, lng: float) -> bool:
    return -90 <= lat <= 90 and -180 <= lng <= 180


def _expand(url: str) -> str:
    """Follow redirects on a short link. Returns the original URL if it cannot."""
    request = urllib.request.Request(
        url,
        # Google serves a consent interstitial without a normal-looking client, and the
        # redirect we need never happens.
        headers={"User-Agent": "Mozilla/5.0 (compatible; OlracSignage/1.0)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.geturl() or url
    except Exception as exc:
        logger.warning("could not expand maps link %s: %s", url, exc)
        return url


def _name_from(url: str) -> str | None:
    """The human place name Google puts in the path, e.g. /maps/place/Phoenix+Mall/."""
    match = re.search(r"/maps/place/([^/@]+)", url)
    if not match:
        return None
    name = urllib.parse.unquote_plus(match.group(1)).strip()
    # A name that is really just the coordinates is no better than the numbers.
    return None if not name or _PAIR.match(name) else name


def _name_from_search(url: str) -> str | None:
    """Place name out of a Google *search* URL.

    The Android share sheet produces share.google links, and those redirect to a search
    result rather than a map — there is no coordinate anywhere in them, only ?q=<name>.
    """
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    for value in query.get("q", []):
        name = value.strip()
        if name and not _PAIR.match(name):
            return name
    return None


def geocode(name: str) -> tuple[float, float] | None:
    """Coordinates for a place name, via OpenStreetMap's keyless geocoder.

    Used only when a link carries a name but no coordinate. One request per location an
    operator sets by hand is well inside Nominatim's acceptable use; it identifies itself
    as required, which is the condition they actually enforce.
    """
    url = ("https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&q="
           + urllib.parse.quote(name))
    request = urllib.request.Request(
        url, headers={"User-Agent": "OlracSignage/1.0 (digital signage fleet management)"}
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            results = json.loads(response.read())
    except Exception as exc:
        logger.warning("geocode failed for %r: %s", name, exc)
        return None
    if not results:
        return None
    lat, lng = float(results[0]["lat"]), float(results[0]["lon"])
    return (lat, lng) if _valid(lat, lng) else None


def parse(link: str) -> tuple[float, float, str | None]:
    """(latitude, longitude, place name or None) from any Google Maps URL.

    Raises MapsLinkError when the link carries no coordinate.
    """
    link = (link or "").strip()
    if not link:
        raise MapsLinkError("No link given.")
    if not link.startswith(("http://", "https://")):
        link = "https://" + link

    parsed = urllib.parse.urlparse(link)
    if not parsed.netloc.endswith(ACCEPTED_HOSTS):
        raise MapsLinkError("That is not a Google Maps link.")

    url = link
    # A short link has nothing to parse until it is followed.
    if parsed.netloc in SHORT_HOSTS and not _AT.search(url) and not _BANG.search(url):
        url = _expand(url)

    # Most precise first: the place marker, then the map centre.
    for pattern in (_BANG, _AT):
        found = pattern.search(url)
        if found:
            lat, lng = float(found.group(1)), float(found.group(2))
            if _valid(lat, lng):
                return lat, lng, _name_from(url)

    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    for key in _QUERY_KEYS:
        for value in query.get(key, []):
            pair = _PAIR.match(value)
            if pair:
                lat, lng = float(pair.group(1)), float(pair.group(2))
                if _valid(lat, lng):
                    return lat, lng, _name_from(url)

    # No coordinate anywhere — but a share.google link still names the place, so resolve
    # the name instead of refusing a link the operator got from Google's own Share button.
    name = _name_from(url) or _name_from_search(url)
    if name:
        point = geocode(name)
        if point:
            return point[0], point[1], name

    raise MapsLinkError(
        "Could not locate that link. Open the place in Google Maps, then use "
        "Share → Copy link."
    )
