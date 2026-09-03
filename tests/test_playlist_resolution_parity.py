"""The dashboard and the player must resolve the same playlist for a screen.

There were two resolvers. `Screen.effective_playlist_id`, which the dashboard serializes,
looked at the screen's own playlist and its *direct* group only; `resolve_screen_playlist`,
which answers the player's sync, also walked the group ancestry and matched dynamic groups.
So a screen inheriting from a grandparent group, or picked up by a dynamic group, played
correctly on the TV while the dashboard reported "Nothing is scheduled on this screen" and
offered to assign a playlist -- for a screen that already had one.

Run directly:  python tests/test_playlist_resolution_parity.py
"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEMP_DIR = tempfile.TemporaryDirectory(prefix="olrac-playlist-parity-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(TEMP_DIR.name) / 'parity.db'}"
os.environ.setdefault("SECRET_KEY", "playlist-parity-secret")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "mock")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "mock")

from backend import models  # noqa: E402
from backend.database import SessionLocal, engine  # noqa: E402
from backend.routers.screens import groups_by_id, resolve_screen_playlist  # noqa: E402


def dashboard_sees(db, screen):
    """Exactly what GET /api/screens/ puts in effective_playlist_id."""
    return screen.resolve_playlist_id(groups_by_id(db, [screen.organization_id]))


def agree(db, screen, expected, label):
    player = resolve_screen_playlist(screen, db)
    dashboard = dashboard_sees(db, screen)
    assert player == expected, f"{label}: player resolved {player}, expected {expected}"
    assert dashboard == player, f"{label}: dashboard says {dashboard}, player plays {player}"
    print(f"  ok  {label} -> playlist {player}")


def main():
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        org = models.Organization(name="Acme", slug="acme")
        other = models.Organization(name="Rival", slug="rival")
        db.add_all([org, other])
        db.commit()

        def playlist(name, organization):
            row = models.Playlist(name=name, organization_id=organization.id)
            db.add(row)
            db.commit()
            return row

        own = playlist("Own loop", org)
        direct = playlist("Direct group loop", org)
        ancestor = playlist("Ancestor loop", org)
        dynamic = playlist("Portrait loop", org)
        foreign = playlist("Rival loop", other)

        def group(name, organization=org, **kwargs):
            row = models.ScreenGroup(name=name, organization_id=organization.id, **kwargs)
            db.add(row)
            db.commit()
            return row

        def screen(device_id, **kwargs):
            row = models.Screen(
                device_id=device_id, name=device_id, organization_id=org.id,
                status="online", **kwargs,
            )
            db.add(row)
            db.commit()
            return row

        # Baselines: the two cases that already worked, so the fix does not trade one
        # broken path for another.
        flat = group("Flat", playlist_id=direct.id)
        agree(db, screen("own", playlist_id=own.id, group_id=flat.id), own.id,
              "a screen's own playlist outranks its group")
        agree(db, screen("direct", group_id=flat.id), direct.id,
              "a screen inherits from its direct group")

        # The regression. A child group with nothing assigned must fall through to the
        # ancestor that does have something -- and the dashboard must see it too.
        grandparent = group("Region", playlist_id=ancestor.id)
        parent = group("Site", parent_id=grandparent.id)
        child = group("Lobby", parent_id=parent.id)
        agree(db, screen("nested", group_id=child.id), ancestor.id,
              "a screen inherits from a grandparent group")

        # The other regression: dynamic groups were invisible to the dashboard.
        group("All portrait", is_dynamic=True, playlist_id=dynamic.id,
              dynamic_criteria={"orientation": 90})
        agree(db, screen("portrait", orientation=90), dynamic.id,
              "a screen is picked up by a dynamic group")
        agree(db, screen("landscape", orientation=0), None,
              "a screen matching no dynamic group still has nothing")

        # A dynamic group must not reach across tenants. groups_by_id is handed several
        # organizations at once when a platform operator lists every screen.
        group("Rival portrait", organization=other, is_dynamic=True, playlist_id=foreign.id,
              dynamic_criteria={"orientation": 270})
        sideways = screen("sideways", orientation=270)
        every_tenant = groups_by_id(db, [org.id, other.id])
        assert sideways.resolve_playlist_id(every_tenant) is None, \
            "a dynamic group matched a screen in another organization"
        print("  ok  a dynamic group does not reach outside its own organization")

        # Cycles predate the validation in routers/groups.py, so the walk stays bounded.
        loop_a = group("Loop A")
        loop_b = group("Loop B", parent_id=loop_a.id)
        loop_a.parent_id = loop_b.id
        db.commit()
        assert dashboard_sees(db, screen("cyclic", group_id=loop_a.id)) is None
        print("  ok  a parent cycle terminates instead of hanging")

        # An emergency broadcast is a takeover, not configuration: the player follows it,
        # the dashboard keeps showing the loop the operator actually assigned.
        emergency = playlist("Evacuate", org)
        held = screen("held", playlist_id=own.id)
        db.add(models.EmergencyBroadcast(
            organization_id=org.id, target_type="all", playlist_id=emergency.id,
            is_active=True,
        ))
        db.commit()
        assert resolve_screen_playlist(held, db) == emergency.id
        assert dashboard_sees(db, held) == own.id, \
            "an emergency takeover overwrote the screen's configured playlist in the dashboard"
        print("  ok  an emergency broadcast overrides the player without rewriting the dashboard")

        print("playlist resolution parity: all checks passed")
    finally:
        db.close()
        engine.dispose()
        TEMP_DIR.cleanup()


if __name__ == "__main__":
    main()
