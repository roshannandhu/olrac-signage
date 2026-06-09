import secrets


def generate_screen_token() -> str:
    """Generate a cryptographically secure opaque screen token (43 chars)."""
    return secrets.token_urlsafe(32)


def generate_pairing_code() -> str:
    """Generate a 6-digit numeric pairing code, zero-padded."""
    return f"{secrets.randbelow(1_000_000):06d}"
