from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

# Per-IP limiting for the endpoints that explicitly ask for it with @limiter.limit --
# the credential-guessing surfaces (login, password change, TV sign-in, device auth).
#
# `default_limits` is deliberately NOT relied on as a blanket cap: slowapi only applies it
# to every route if SlowAPIMiddleware is installed, which it is not, so nothing here rate
# limits an undecorated endpoint. That is the intended shape rather than an omission. A
# whole mall of screens sits behind one NAT public IP, so a global per-IP cap counts a
# 50-screen site as a single client and would take the site offline exactly when every TV
# reconnects at once -- a power cut, which is when it can least afford it. Add the
# middleware only alongside a key_func that identifies the device rather than the exit IP.
def client_key(request: Request) -> str:
    """Who to count this request against.

    slowapi's get_remote_address returns request.client.host, which behind a reverse proxy
    -- Render, Fly, any managed host -- is the PROXY, identical for every caller on earth.
    Uvicorn only honours X-Forwarded-For from 127.0.0.1 unless told otherwise, so the
    header alone does not fix it. Left unhandled this turns every per-IP cap into a global
    one: a 5/minute login limit becomes five logins per minute for the whole product, and
    the device-auth cap becomes five TVs per minute for the entire fleet.

    The leftmost X-Forwarded-For entry is the original client. It is client-controlled and
    therefore spoofable, which is acceptable here: the worst a forger achieves is spreading
    their own attempts across buckets, exactly what an attacker with a botnet gets anyway.
    Counting everyone as one caller is the far worse failure.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return get_remote_address(request)


limiter = Limiter(key_func=client_key)
