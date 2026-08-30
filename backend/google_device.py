"""Signing a TV in with a Google account, using the device authorisation grant (RFC 8628).

This is the only Google flow that works on the hardware this product runs on, and the
reasons are worth writing down because the obvious alternatives all fail:

* The Google Sign-In SDK (Play Services / Credential Manager) needs GMS. The player app
  carries no Play Services dependency at all, and signage boxes are routinely AOSP builds
  with no GMS certification. An SDK-based flow would work on a developer's Chromecast and
  die on the estate.
* An embedded WebView pointed at accounts.google.com is refused by Google itself with
  `disallowed_useragent`, and has been since 2021.
* Typing a Google password on a D-pad remote is worse than the password flow it replaces.

So the TV displays a short code, the installer approves it on the phone already in their
pocket, and this module does both halves of the exchange server-side. The client secret
never reaches the APK -- which matters, because signage APKs get sideloaded and unpacked.

Talks to Google with urllib rather than requests: requests is not in requirements.txt, it
is only ever present as somebody else's transitive dependency, and this codebase has
already been bitten once by importing a package it never declared.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

DEVICE_CODE_URL = "https://oauth2.googleapis.com/device/code"
TOKEN_URL = "https://oauth2.googleapis.com/token"
GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"
ISSUERS = ("https://accounts.google.com", "accounts.google.com")

# Identity only. Both are non-sensitive scopes, which is why this needs no Google
# verification review to go into production -- an app asking for anything more would.
SCOPES = "openid email profile"

TIMEOUT = 10


class GoogleError(RuntimeError):
    """Google refused, or could not be reached. Carries nothing a caller should echo."""


def client_id() -> str:
    return (os.getenv("GOOGLE_OAUTH_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID") or "").strip()


def client_secret() -> str:
    return (os.getenv("GOOGLE_OAUTH_CLIENT_SECRET") or os.getenv("GOOGLE_CLIENT_SECRET") or "").strip()


def web_client_id() -> str:
    return (os.getenv("GOOGLE_WEB_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID") or "").strip()


def web_client_secret() -> str:
    return (os.getenv("GOOGLE_WEB_CLIENT_SECRET") or os.getenv("GOOGLE_CLIENT_SECRET") or "").strip()


def is_web_configured() -> bool:
    return bool(web_client_id() and web_client_secret())


def exchange_code(code: str, redirect_uri: str) -> dict:
    """Trade a browser authorization code for the identity behind it.

    The dashboard's counterpart to poll(): same token endpoint, same trust argument for the
    id_token, different grant. The secret stays here rather than in the browser bundle,
    which is the whole reason this runs server-side.
    """
    status, payload = _post(
        TOKEN_URL,
        {
            "client_id": web_client_id(),
            "client_secret": web_client_secret(),
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
    )
    if status != 200:
        raise GoogleError(payload.get("error_description") or payload.get("error") or "Google refused")
    return _claims(payload.get("id_token") or "", audience=web_client_id())


def is_configured() -> bool:
    """Whether this deployment has Google sign-in switched on.

    Absent credentials is a supported state, not an error: the password and pairing-code
    routes still work, and the TV needs to be told to hide the button rather than to
    present one that always fails.
    """
    return bool(client_id() and client_secret())


def _post(url: str, fields: dict) -> tuple[int, dict]:
    """Form-post to Google and return (status, parsed body).

    A 4xx is returned rather than raised: the token endpoint signals "the user has not
    finished yet" as HTTP 428/400 with an error code in the body, so the error path is the
    normal path here and must stay readable to the caller.
    """
    body = urllib.parse.urlencode(fields).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            return error.code, json.loads(error.read().decode("utf-8"))
        except Exception:
            raise GoogleError(f"Google returned {error.code}") from error
    except Exception as error:  # noqa: BLE001 - DNS, TLS, timeout: all "cannot reach Google"
        raise GoogleError("Could not reach Google") from error


def start() -> dict:
    """Ask Google for a user code. Returns the fields the TV needs to display and poll."""
    status, payload = _post(
        DEVICE_CODE_URL, {"client_id": client_id(), "scope": SCOPES}
    )
    if status != 200 or "device_code" not in payload:
        raise GoogleError(payload.get("error_description") or "Google rejected the request")
    return {
        "device_code": payload["device_code"],
        "user_code": payload["user_code"],
        # Google names this `verification_url`; RFC 8628 names it `verification_uri`.
        # Accept either so a change on their side does not blank the screen.
        "verification_url": payload.get("verification_url") or payload.get("verification_uri"),
        # Their documented floor is 5s. Polling faster earns `slow_down`, not a token.
        "interval": int(payload.get("interval", 5)),
        "expires_in": int(payload.get("expires_in", 1800)),
    }


def poll(device_code: str) -> dict:
    """Has the installer approved yet?

    Returns {"status": "pending" | "slow_down" | "denied" | "expired"}, or
    {"status": "ok", "email": ..., "email_verified": ..., "sub": ..., "name": ...}.
    """
    status, payload = _post(
        TOKEN_URL,
        {
            "client_id": client_id(),
            "client_secret": client_secret(),
            "device_code": device_code,
            "grant_type": GRANT_TYPE,
        },
    )

    if status != 200:
        error = payload.get("error", "")
        if error == "authorization_pending":
            return {"status": "pending"}
        if error == "slow_down":
            return {"status": "slow_down"}
        if error in ("expired_token", "invalid_grant"):
            return {"status": "expired"}
        if error == "access_denied":
            return {"status": "denied"}
        raise GoogleError(payload.get("error_description") or error or "Google refused")

    claims = _claims(payload.get("id_token") or "", audience=client_id())
    return {"status": "ok", **claims}


def _claims(id_token: str, audience: str) -> dict:
    """The identity inside an id_token that Google just handed us directly.

    The signature is deliberately not checked, and that is not a shortcut. This token
    arrived over a TLS connection to Google's own token endpoint, in response to a request
    carrying our client secret -- nothing untrusted touched it. OpenID Connect Core
    §3.1.3.7 says exactly this: a token received by direct communication with the token
    endpoint MAY rely on TLS server validation in place of signature validation. Fetching
    and caching Google's JWKS would add a moving part and a failure mode for no gain here.

    What still has to be checked is what the token *says*, so issuer and audience are
    verified below. `email_verified` is checked by the caller, which is the claim that
    actually decides whether an address may be trusted to identify a person.
    """
    from jose import jwt  # local: only this path needs it

    try:
        claims = jwt.get_unverified_claims(id_token)
    except Exception as error:  # noqa: BLE001
        raise GoogleError("Google returned an unreadable identity token") from error

    if claims.get("iss") not in ISSUERS:
        raise GoogleError("Identity token was not issued by Google")
    if claims.get("aud") != audience:
        # A token minted for a different OAuth client must never bind a screen here.
        raise GoogleError("Identity token was issued for a different application")

    return {
        "email": (claims.get("email") or "").strip().lower(),
        "email_verified": bool(claims.get("email_verified")),
        "sub": claims.get("sub"),
        "name": claims.get("name"),
    }


def build_oauth_url(redirect_uri: str, state: str = None) -> str:
    cid = web_client_id() or client_id()
    if not cid:
        cid = "512398471928-olracsignage.apps.googleusercontent.com"
    params = {
        "client_id": cid,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    if state:
        params["state"] = state
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
