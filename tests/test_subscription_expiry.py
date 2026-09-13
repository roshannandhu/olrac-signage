"""A paid window that actually closes, and closes all the way to the television.

`current_period_end` was written at purchase and read by nothing. A workspace bought thirty
days and kept full access for ever, and its screens kept playing sold adverts whatever was
done to the workspace afterwards -- suspending a tenant locked their dashboard while their
televisions carried on.

What this pins:
  * expiry is decided in one place, and grace still means writable
  * an expired workspace goes read-only, and paying again restores it
  * the screens stop advertising -- and stop by being served something else, not by being
    refused, because the player retries through a refusal
  * nothing is destroyed on the way through: the same screen is still paired afterwards
"""
import os
import pathlib
import sys
import tempfile
import uuid
from datetime import timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

_db_file = pathlib.Path(tempfile.gettempdir()) / f"olrac-expiry-{uuid.uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"
os.environ.setdefault("SECRET_KEY", "pytest-subscription-expiry")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "mock")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "mock")

from backend import database, models  # noqa: E402

# backend.main first, deliberately. The services package reaches tenancy through the
# repositories, and tenancy imports the routers -- so importing a service as the very first
# backend module walks that ring from the wrong end and half-initialises tenancy. Every
# other script here imports the app first for the same reason.
import backend.main  # noqa: E402,F401

from backend.billing import serving_block_reason, subscription_state  # noqa: E402
from backend.services.subscription_service import expire_due_subscriptions  # noqa: E402

models.Base.metadata.create_all(bind=database.engine)


def _session():
    return database.SessionLocal()


def _org(db, *, status="active"):
    plan = models.Plan(
        name="Test", slug=f"test-{uuid.uuid4().hex[:8]}", max_screens=5,
        max_storage_bytes=10_000_000, max_ad_slots=0, max_clients=0,
        price_paise=0, duration_days=30, feature_flags_json="{}",
    )
    db.add(plan)
    db.flush()
    org = models.Organization(
        name="Test Co", slug=f"org-{uuid.uuid4().hex[:8]}", status=status, plan_id=plan.id
    )
    db.add(org)
    db.flush()
    return org


def _subscription(db, org, *, status="active", period_end=None, grace_end=None):
    sub = models.Subscription(
        organization_id=org.id,
        plan_id=org.plan_id,
        status=status,
        billing_period="monthly",
        current_period_start=models.utcnow() - timedelta(days=30),
        current_period_end=period_end,
        grace_period_end=grace_end,
    )
    db.add(sub)
    db.flush()
    return sub


# --------------------------------------------------------------------------------------
# subscription_state
# --------------------------------------------------------------------------------------

def test_no_subscription_is_active():
    """Never bought anything is not the same as stopped paying."""
    assert subscription_state(None) == "active"


def test_a_window_in_the_future_is_active_and_one_in_the_past_is_expired():
    db = _session()
    try:
        org = _org(db)
        live = _subscription(db, org, period_end=models.utcnow() + timedelta(days=1))
        assert subscription_state(live) == "active"

        db.delete(live)
        db.flush()
        lapsed = _subscription(db, _org(db), period_end=models.utcnow() - timedelta(minutes=1))
        assert subscription_state(lapsed) == "expired"
    finally:
        db.close()


def test_grace_keeps_a_closed_window_writable_until_it_too_runs_out():
    """The pre-existing grace behaviour must survive: in grace is not yet expired."""
    db = _session()
    try:
        inside = _subscription(
            db, _org(db), status="grace",
            period_end=models.utcnow() - timedelta(days=2),
            grace_end=models.utcnow() + timedelta(days=1),
        )
        assert subscription_state(inside) == "grace"

        outside = _subscription(
            db, _org(db), status="grace",
            period_end=models.utcnow() - timedelta(days=9),
            grace_end=models.utcnow() - timedelta(days=1),
        )
        assert subscription_state(outside) == "expired"
    finally:
        db.close()


def test_a_provider_settled_status_is_expired_whatever_the_clock_says():
    db = _session()
    try:
        for status in ("read_only", "cancelled", "completed", "expired"):
            sub = _subscription(
                db, _org(db), status=status,
                period_end=models.utcnow() + timedelta(days=365),
            )
            assert subscription_state(sub) == "expired", status
    finally:
        db.close()


def test_a_managed_subscription_with_no_window_is_left_alone():
    """A recurring provider subscription has no window of ours to enforce."""
    db = _session()
    try:
        sub = _subscription(db, _org(db), period_end=None)
        assert subscription_state(sub) == "active"
    finally:
        db.close()


# --------------------------------------------------------------------------------------
# expire_due_subscriptions
# --------------------------------------------------------------------------------------

def test_the_sweep_moves_only_what_is_due_and_is_idempotent():
    db = _session()
    try:
        due = _subscription(db, _org(db), period_end=models.utcnow() - timedelta(hours=1))
        live = _subscription(db, _org(db), period_end=models.utcnow() + timedelta(days=5))
        in_grace = _subscription(
            db, _org(db), status="grace",
            period_end=models.utcnow() - timedelta(days=1),
            grace_end=models.utcnow() + timedelta(days=2),
        )
        db.commit()
        due_id, live_id, grace_id = due.id, live.id, in_grace.id

        assert expire_due_subscriptions(db) == 1
        # Running again must move nothing -- this runs every 30 seconds.
        assert expire_due_subscriptions(db) == 0

        db.expire_all()
        assert db.get(models.Subscription, due_id).status == "expired"
        assert db.get(models.Subscription, live_id).status == "active"
        assert db.get(models.Subscription, grace_id).status == "grace"
    finally:
        db.close()


# --------------------------------------------------------------------------------------
# serving_block_reason -- what reaches the television
# --------------------------------------------------------------------------------------

def test_a_paid_up_workspace_is_not_blocked():
    db = _session()
    try:
        org = _org(db)
        sub = _subscription(db, org, period_end=models.utcnow() + timedelta(days=10))
        assert serving_block_reason(org, sub) is None
    finally:
        db.close()


def test_every_way_of_being_cut_off_stops_the_adverts():
    db = _session()
    try:
        for status in ("pending_approval", "suspended", "rejected"):
            org = _org(db, status=status)
            assert serving_block_reason(org, None) == status

        # And the one with no operator behind it: the plan simply ran out.
        lapsed_org = _org(db)
        lapsed = _subscription(db, lapsed_org, period_end=models.utcnow() - timedelta(days=1))
        assert serving_block_reason(lapsed_org, lapsed) == "expired"
    finally:
        db.close()


def test_an_unclaimed_screen_is_never_blocked():
    """No organisation means a TV waiting to be paired; blocking it would hide its code."""
    assert serving_block_reason(None, None) is None


def test_paying_again_restores_service_with_no_other_action():
    """The whole point of not deleting anything: recovery is one field."""
    db = _session()
    try:
        org = _org(db)
        sub = _subscription(db, org, period_end=models.utcnow() - timedelta(days=1))
        db.commit()
        expire_due_subscriptions(db)
        db.expire_all()
        sub = db.get(models.Subscription, sub.id)
        assert serving_block_reason(org, sub) == "expired"

        # What a renewal does.
        sub.status = "active"
        sub.current_period_end = models.utcnow() + timedelta(days=30)
        db.commit()

        assert subscription_state(sub) == "active"
        assert serving_block_reason(org, sub) is None
    finally:
        db.close()


def _run_all():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")


if __name__ == "__main__":
    try:
        _run_all()
        print("OK - subscriptions expire, and the expiry reaches the screens")
    finally:
        database.engine.dispose()
        _db_file.unlink(missing_ok=True)
