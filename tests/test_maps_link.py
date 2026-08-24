"""Turning a pasted Google Maps link into a coordinate.

This module had no tests, which is how two separate faults in the Pin button survived:
the request never reached the handler at all, and when it did, a link Google had refused
was reported as one that merely lacked a coordinate.

No network. `_expand` is stubbed everywhere a short link is involved, so these run the
parsing rules rather than Google's uptime.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from backend import maps_link  # noqa: E402


@pytest.fixture
def expands_to(monkeypatch):
    """Point the redirect-follower at a fixed destination."""
    def _set(destination: str):
        monkeypatch.setattr(maps_link, "_expand", lambda url: destination)
    return _set


@pytest.fixture
def nominatim(monkeypatch):
    """Answer the geocoder from a canned reply, and record how often it was asked.

    Clears the cache and the rate-limit stamp too, so one test cannot read another's
    cached result or be put to sleep by another's timestamp.
    """
    import json as _json

    maps_link._geocode_cache.clear()
    monkeypatch.setattr(maps_link, "_geocode_last_call", 0.0)
    calls: list[str] = []

    class _Reply:
        def __init__(self, payload):
            self._payload = payload

        def read(self):
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def _set(reply):
        def fake_urlopen(request, timeout=None):
            calls.append(request.full_url)
            if isinstance(reply, Exception):
                raise reply
            body = reply if isinstance(reply, str) else _json.dumps(reply)
            return _Reply(body.encode())

        monkeypatch.setattr(maps_link.urllib.request, "urlopen", fake_urlopen)
        return calls

    return _set


# --- coordinates already in the link ---------------------------------------------------

def test_the_place_marker_wins_over_the_map_centre():
    # !3d/!4d is the place itself; @ is wherever the map happened to be centred.
    lat, lng, _ = maps_link.parse(
        "https://www.google.com/maps/place/X/@10.1,76.1,17z/data=!3d9.9312!4d76.2673"
    )
    assert (round(lat, 4), round(lng, 4)) == (9.9312, 76.2673)


def test_the_map_centre_is_used_when_there_is_no_marker():
    lat, lng, name = maps_link.parse(
        "https://www.google.com/maps/place/Lulu+Mall/@10.0261,76.3081,17z"
    )
    assert (lat, lng) == (10.0261, 76.3081)
    assert name == "Lulu Mall"


def test_a_query_coordinate_is_accepted():
    lat, lng, _ = maps_link.parse("https://maps.google.com/?q=9.9312,76.2673")
    assert (lat, lng) == (9.9312, 76.2673)


def test_a_name_that_is_only_a_coordinate_is_not_a_name():
    _, _, name = maps_link.parse(
        "https://www.google.com/maps/place/9.9312,76.2673/@9.9312,76.2673,17z"
    )
    assert name is None


def test_an_out_of_range_coordinate_is_refused():
    # 999 is not a latitude; better to refuse than to pin a screen into the sea.
    with pytest.raises(maps_link.MapsLinkError):
        maps_link.parse("https://www.google.com/maps/@999.0000,76.2673,17z")


# --- what the operator actually pastes -------------------------------------------------

def test_a_dead_share_link_says_so_rather_than_blaming_the_coordinate(expands_to):
    # Google answers a dead share.google link with 200 and a redirect to its own error
    # page, not a 404. Reported as "no coordinate" it reads as a fault in the app, and the
    # advice is to re-copy a link that will never work.
    expands_to("https://share.google/error")
    with pytest.raises(maps_link.MapsLinkError) as caught:
        maps_link.parse("https://share.google/zZF5G9zS8VOzSbvpF")
    assert "expired" in str(caught.value)


def test_a_share_link_that_resolves_to_a_real_place_works(expands_to):
    expands_to("https://www.google.com/maps/place/Phoenix+Mall/@12.9916,77.5946,17z")
    lat, lng, name = maps_link.parse("https://share.google/abcdefg")
    assert (lat, lng) == (12.9916, 77.5946)
    assert name == "Phoenix Mall"


def test_a_search_link_falls_back_to_geocoding_the_name(expands_to, monkeypatch):
    # share.google often redirects to a search result with no coordinate anywhere, only
    # ?q=<name>. Refusing those would reject the link Google's own Share button produces.
    expands_to("https://www.google.com/search?q=Lulu+Mall+Kochi")
    monkeypatch.setattr(maps_link, "geocode", lambda name: (10.0261, 76.3081))
    lat, lng, name = maps_link.parse("https://share.google/abcdefg")
    assert (lat, lng) == (10.0261, 76.3081)
    assert name == "Lulu Mall Kochi"


def test_a_name_that_cannot_be_geocoded_is_refused(expands_to, monkeypatch):
    expands_to("https://www.google.com/search?q=Nowhere+At+All")
    monkeypatch.setattr(maps_link, "geocode", lambda name: None)
    with pytest.raises(maps_link.MapsLinkError):
        maps_link.parse("https://share.google/abcdefg")


# --- geocoding, which every screen in a fleet goes through separately -------------------

MATCH = [{"lat": "10.0274822", "lon": "76.3079131"}]


def test_the_same_place_is_only_looked_up_once(nominatim):
    # A location is set per screen, and screens in one mall share a place name. Asking
    # Nominatim again for an answer we already have is what walks into their rate limit.
    calls = nominatim(MATCH)
    assert maps_link.geocode("Lulu Mall Kochi") == (10.0274822, 76.3079131)
    assert maps_link.geocode("  lulu mall KOCHI ") == (10.0274822, 76.3079131)
    assert len(calls) == 1, "the second lookup should have come from the cache"


def test_a_failed_lookup_is_not_cached(nominatim):
    # Caching a timeout would leave that location unresolvable until the process restarts.
    calls = nominatim(TimeoutError("nominatim is slow today"))
    assert maps_link.geocode("Lulu Mall Kochi") is None
    nominatim(MATCH)
    assert maps_link.geocode("Lulu Mall Kochi") == (10.0274822, 76.3079131)
    # Two calls, not one: a remembered failure would have returned None without asking
    # again. `calls` is shared across both stubs, so it counts the whole test.
    assert len(calls) == 2, "the failure should have been retried, not cached"


def test_no_match_is_reported_rather_than_raised(nominatim):
    nominatim([])
    assert maps_link.geocode("Somewhere that does not exist") is None


def test_a_reply_in_an_unexpected_shape_does_not_escape_as_a_500(nominatim):
    # This used to be an unguarded results[0]["lat"], so a changed reply reached the
    # operator as a blank failure rather than "could not locate".
    for reply in ([{"latitude": "10.0"}], [{}], "not json at all", [None]):
        nominatim(reply)
        maps_link._geocode_cache.clear()
        assert maps_link.geocode("Lulu Mall Kochi") is None


def test_a_nonsense_coordinate_from_the_geocoder_is_refused(nominatim):
    nominatim([{"lat": "999.0", "lon": "76.3"}])
    assert maps_link.geocode("Lulu Mall Kochi") is None


# --- input the operator gets wrong -----------------------------------------------------

def test_an_empty_link_is_refused():
    with pytest.raises(maps_link.MapsLinkError):
        maps_link.parse("   ")


def test_a_non_google_link_is_refused():
    with pytest.raises(maps_link.MapsLinkError):
        maps_link.parse("https://example.com/maps/@9.9312,76.2673,17z")


def test_a_lookalike_domain_is_refused():
    # endswith() on the host is what accepts these, so a domain merely ending in the same
    # letters must not slip through as Google.
    with pytest.raises(maps_link.MapsLinkError):
        maps_link.parse("https://nedgoogle.com/maps/@9.9312,76.2673,17z")


def test_userinfo_cannot_disguise_a_foreign_host():
    # "https://www.google.com@evil.com/..." fetches evil.com. The accepted-host check runs
    # on the parsed hostname so the part before the @ cannot vouch for it.
    with pytest.raises(maps_link.MapsLinkError):
        maps_link.parse("https://www.google.com@evil.example/maps/@9.9312,76.2673,17z")


def test_a_genuine_google_subdomain_is_still_accepted():
    # Tightening the host check must not start refusing the real thing.
    lat, lng, _ = maps_link.parse("https://www.google.co.in/maps/@9.9312,76.2673,17z")
    assert (lat, lng) == (9.9312, 76.2673)


def test_the_host_check_ignores_case_and_port():
    lat, lng, _ = maps_link.parse("https://WWW.Google.COM:443/maps/@9.9312,76.2673,17z")
    assert (lat, lng) == (9.9312, 76.2673)


def test_a_link_pasted_without_its_scheme_still_works():
    # Copying from a phone regularly drops the https://.
    lat, lng, _ = maps_link.parse("www.google.com/maps/@9.9312,76.2673,17z")
    assert (lat, lng) == (9.9312, 76.2673)


def test_the_error_page_check_matches_the_path_not_the_name(expands_to):
    # A place legitimately called "error" must not be mistaken for Google's error page.
    expands_to("https://www.google.com/maps/place/Trial+and+error/@9.9312,76.2673,17z")
    lat, lng, name = maps_link.parse("https://share.google/abcdefg")
    assert (lat, lng) == (9.9312, 76.2673)
    assert name == "Trial and error"
