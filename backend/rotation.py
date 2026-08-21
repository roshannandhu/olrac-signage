"""Resolve the rotation a screen should apply to one playlist item.

The player must not reason about this. It receives a single number and turns the surface
by that many degrees, so all the precedence lives here and is testable without a device.

Precedence, highest first:
  1. PlaylistItem.rotation  — an explicit per-item override
  2. Screen.orientation     — the panel's mount, auto-detected or set by an operator
  3. 0                      — landscape, the default

The value returned is the rotation to apply *on top of* whatever the decoder already does.
Media3 honours the `rotate` metadata tag that phone footage carries, so the content's own
rotation is deliberately NOT added here — doing so rotates such clips twice.
"""

VALID_ROTATIONS = (0, 90, 180, 270)


def normalise(degrees) -> int:
    """Coerce anything to one of 0/90/180/270, defaulting to 0."""
    try:
        value = int(degrees) % 360
    except (TypeError, ValueError):
        return 0
    return value if value in VALID_ROTATIONS else 0


def resolve_rotation(item, screen) -> int:
    """Degrees the player should rotate this item on this screen."""
    item_rotation = getattr(item, "rotation", None)
    if item_rotation is not None:
        return normalise(item_rotation)
    return normalise(getattr(screen, "orientation", 0))
