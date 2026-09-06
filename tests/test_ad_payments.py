"""A booking's paid state is the shadow of a payment record, not a free-floating boolean.

`AdPlacement.is_paid` used to be the whole story: one flag, settable through the same
generic PUT that edits dates and price. It could say a campaign was paid while recording
no amount, no method, no date and no one accountable -- so a mis-click looked exactly like
a receipt, and "did they pay by UPI or was that the cheque that bounced?" had no answer.

What is pinned here:

* Recording a payment is the ONLY way a booking becomes paid. The generic PUT can no
  longer flip the flag, so the receipt and the flag cannot disagree.
* One settlement per booking. Recording again corrects the record rather than stacking a
  second one -- the deliberate ceiling, and the thing that would have to change first if
  instalments are ever wanted.
* Clearing it puts the booking back to unpaid, including for bookings marked paid before
  payments existed and which therefore have no row to delete.
* "Paid" means the balance is ZERO, not that some money arrived. A part payment leaves the
  booking part paid and reports what is still owed, and anything that moves the total --
  an extension, an upgrade, a corrected price -- re-settles it against what was received.
* A payment belongs to its tenant and its booking, and dies with the booking.

Throwaway Postgres database. Run directly:  python tests/test_ad_payments.py
"""
import os
import sys
import uuid
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SCRATCH = f"olrac_adpayments_{uuid.uuid4().hex[:8]}"
os.environ["DATABASE_URL"] = f"postgresql://olrac:olrac_password@localhost:5432/{SCRATCH}"
os.environ["SECRET_KEY"] = "ad-payments-secret"
os.environ["AWS_ACCESS_KEY_ID"] = "mock"

import psycopg2  # noqa: E402
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT  # noqa: E402

admin = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/postgres")
admin.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
admin.cursor().execute(f'CREATE DATABASE "{SCRATCH}" OWNER olrac')

db = None
try:
    from fastapi.testclient import TestClient  # noqa: E402
    from backend import models  # noqa: E402
    from backend.database import SessionLocal, engine  # noqa: E402
    from backend.main import app  # noqa: E402
    from backend.routers.auth import create_access_token, get_password_hash  # noqa: E402

    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    acme = models.Organization(name="Acme", slug="acme")
    rival = models.Organization(name="Rival", slug="rival")
    db.add_all([acme, rival]); db.commit()
    owner = models.User(organization_id=acme.id, username="owner@acme.test",
                        hashed_password=get_password_hash("x"), role="owner", is_active=True)
    intruder = models.User(organization_id=rival.id, username="owner@rival.test",
                           hashed_password=get_password_hash("x"), role="owner", is_active=True)
    db.add_all([owner, intruder]); db.commit()

    ad = models.Content(organization_id=acme.id, type="video", file_url="/uploads/1/a.mp4",
                        name="Summer Sale", status="ready", duration_ms=30_000)
    db.add(ad); db.commit()
    screen = models.Screen(organization_id=acme.id, name="Lobby", status="online")
    db.add(screen); db.commit()

    http = TestClient(app)
    auth = {"Authorization": f"Bearer {create_access_token({'sub': owner.username})}"}
    rival_auth = {"Authorization": f"Bearer {create_access_token({'sub': intruder.username})}"}
    now = models.utcnow()

    booking = http.post("/api/placements/", headers=auth, json={
        "content_id": ad.id, "advertiser": "Brightmart", "price_paise": 2500000,
        "starts_at": now.isoformat(), "ends_at": (now + timedelta(days=30)).isoformat(),
        "targets": [{"screen_id": screen.id}],
    })
    assert booking.status_code == 201, booking.text
    booking_id = booking.json()["id"]
    assert booking.json()["is_paid"] is False, "a new booking is not paid"
    assert booking.json()["payment"] is None, booking.json()
    print("  ok  a new booking starts unpaid, with no payment record")

    # --- the flag can no longer be set without a receipt behind it -----------------------
    blind = http.put(f"/api/placements/{booking_id}", headers=auth, json={"is_paid": True})
    assert blind.status_code == 200, blind.text
    assert blind.json()["is_paid"] is False, (
        "a blind PUT marked the booking paid -- is_paid must be the shadow of a payment "
        "record, or a mis-click is indistinguishable from a receipt"
    )
    assert blind.json()["payment"] is None, blind.json()
    print("  ok  the generic PUT can no longer mark a booking paid")

    # --- recording a payment is what settles it ------------------------------------------
    paid = http.post(f"/api/placements/{booking_id}/payment", headers=auth, json={
        "amount_paise": 2500000, "method": "upi", "reference": "UTR9988776655",
        "notes": "Settled at the counter",
    })
    assert paid.status_code == 201, paid.text
    body = paid.json()
    assert body["is_paid"] is True, body
    payment = body["payment"]
    assert payment["amount_paise"] == 2500000, payment
    assert payment["method"] == "upi", payment
    assert payment["reference"] == "UTR9988776655", payment
    assert payment["recorded_by"] == "owner@acme.test", (
        f"the payment must record who took it, got {payment['recorded_by']!r}"
    )
    assert payment["paid_at"], payment
    print("  ok  recording a payment settles the booking and keeps amount, method, reference and taker")

    # --- one settlement per booking; recording again corrects it -------------------------
    corrected = http.post(f"/api/placements/{booking_id}/payment", headers=auth, json={
        "amount_paise": 2400000, "method": "cheque", "reference": "CHQ 41003",
    })
    assert corrected.status_code == 201, corrected.text
    assert corrected.json()["payment"]["method"] == "cheque", corrected.json()["payment"]
    assert corrected.json()["payment"]["amount_paise"] == 2400000, corrected.json()["payment"]
    assert corrected.json()["payment"]["reference"] == "CHQ 41003", corrected.json()["payment"]
    rows = db.query(models.AdPayment).filter(models.AdPayment.placement_id == booking_id).count()
    assert rows == 1, f"re-recording stacked {rows} payments; one booking settles once"
    print("  ok  re-recording corrects the settlement rather than stacking a second one")

    # --- an unknown method is refused, so the column cannot fill with typos ---------------
    bad = http.post(f"/api/placements/{booking_id}/payment", headers=auth,
                    json={"amount_paise": 100, "method": "crypto"})
    assert bad.status_code == 422, bad.text
    mixed_case = http.post(f"/api/placements/{booking_id}/payment", headers=auth,
                           json={"amount_paise": 100, "method": "  Bank_Transfer "})
    assert mixed_case.status_code == 201, mixed_case.text
    assert mixed_case.json()["payment"]["method"] == "bank_transfer", (
        "a method typed with stray case or spacing must normalise, not create a second "
        "spelling of the same method"
    )
    print("  ok  an unknown method is refused and a sloppily typed one is normalised")

    # --- clearing puts it back to unpaid --------------------------------------------------
    cleared = http.delete(f"/api/placements/{booking_id}/payment", headers=auth)
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["is_paid"] is False, cleared.json()
    assert cleared.json()["payment"] is None, cleared.json()
    assert db.query(models.AdPayment).filter(models.AdPayment.placement_id == booking_id).count() == 0
    print("  ok  clearing a payment returns the booking to unpaid")

    # A booking marked paid before payments existed has no row to delete. Clearing must
    # still work, or a legacy campaign is stuck paid forever.
    legacy = models.AdPlacement(
        organization_id=acme.id, content_id=ad.id, advertiser="Legacy Co",
        price_paise=100000, is_paid=True, starts_at=now, ends_at=now + timedelta(days=10),
    )
    db.add(legacy); db.commit()
    legacy_cleared = http.delete(f"/api/placements/{legacy.id}/payment", headers=auth)
    assert legacy_cleared.status_code == 200, legacy_cleared.text
    assert legacy_cleared.json()["is_paid"] is False, (
        "a booking marked paid before payments were recorded has no row to delete, and "
        "leaving the flag set would make it permanently unclearable"
    )
    print("  ok  a legacy booking with no payment row can still be marked unpaid")

    # --- a part payment is a part payment ------------------------------------------------
    # The flag is read everywhere as "settled in full". Setting it on the first rupee is
    # what let a 5,000 deposit against a 50,000 campaign print "Paid in full" on the ad
    # page while the invoice for the same booking chased 45,000.
    part = models.AdPlacement(
        organization_id=acme.id, content_id=ad.id, advertiser="Deposit Co",
        price_paise=5000000, starts_at=now, ends_at=now + timedelta(days=30),
    )
    db.add(part); db.commit()

    deposit = http.post(f"/api/placements/{part.id}/payment", headers=auth,
                        json={"amount_paise": 500000, "method": "upi"})
    assert deposit.status_code == 201, deposit.text
    body = deposit.json()
    assert body["is_paid"] is False, (
        "a 5,000 deposit against a 50,000 booking marked it paid in full"
    )
    assert body["payment_status"] == "part_paid", body
    assert body["amount_paid_paise"] == 500000, body
    assert body["balance_due_paise"] == 4500000, body
    print("  ok  a part payment leaves the booking part paid, with the balance reported")

    settled = http.post(f"/api/placements/{part.id}/payment", headers=auth,
                        json={"amount_paise": 5000000, "method": "upi"})
    assert settled.json()["is_paid"] is True, settled.json()
    assert settled.json()["payment_status"] == "paid", settled.json()
    assert settled.json()["balance_due_paise"] == 0, settled.json()
    print("  ok  paying the rest settles it")

    # --- selling more re-opens the balance ------------------------------------------------
    # An extension or an upgrade moves the TOTAL. A booking settled against the old total
    # is not settled against the new one, and saying otherwise is how airtime gets given
    # away: the operator sees "Paid" and never chases the difference.
    extended = http.post(f"/api/placements/{part.id}/extensions", headers=auth, json={
        "extended_to": (now + timedelta(days=60)).isoformat(),
        "additional_price_paise": 1500000,
    })
    assert extended.status_code == 201, extended.text
    assert extended.json()["is_paid"] is False, (
        "a booking stayed 'paid' after 15,000 more was sold against it"
    )
    assert extended.json()["payment_status"] == "part_paid", extended.json()
    assert extended.json()["balance_due_paise"] == 1500000, extended.json()
    print("  ok  selling an extension against a settled booking re-opens the balance")

    extension_id = extended.json()["extensions"][0]["id"]
    pulled = http.delete(f"/api/placements/{part.id}/extensions/{extension_id}", headers=auth)
    assert pulled.status_code == 200, pulled.text
    assert pulled.json()["is_paid"] is True, (
        "cancelling the extension left the booking owing money it no longer owes"
    )
    print("  ok  cancelling it settles the booking again")

    # --- correcting the price re-settles too ----------------------------------------------
    repriced = http.put(f"/api/placements/{part.id}", headers=auth,
                        json={"price_paise": 6000000})
    assert repriced.json()["balance_due_paise"] == 1000000, repriced.json()
    assert repriced.json()["is_paid"] is False, repriced.json()
    print("  ok  correcting the price re-settles against what was already received")

    # A booking marked paid before payments existed reports its price as received rather
    # than reading as owing the lot again -- that flag is the only receipt it has.
    legacy_flagged = models.AdPlacement(
        organization_id=acme.id, content_id=ad.id, advertiser="Before Payments",
        price_paise=250000, is_paid=True, starts_at=now, ends_at=now + timedelta(days=10),
    )
    db.add(legacy_flagged); db.commit()
    seen = http.get(f"/api/placements/?content_id={ad.id}", headers=auth).json()
    row = next(p for p in seen if p["id"] == legacy_flagged.id)
    assert row["payment_status"] == "paid", row
    assert row["balance_due_paise"] == 0, row
    print("  ok  a booking marked paid before payments existed still reads as settled")

    # --- tenant isolation -----------------------------------------------------------------
    for call in (
        lambda: http.post(f"/api/placements/{booking_id}/payment", headers=rival_auth,
                          json={"amount_paise": 1, "method": "cash"}),
        lambda: http.delete(f"/api/placements/{booking_id}/payment", headers=rival_auth),
    ):
        assert call().status_code == 404, "another tenant reached this booking's payment"
    print("  ok  another tenant can neither record nor clear a payment on this booking")

    # --- the payment dies with the booking -------------------------------------------------
    http.post(f"/api/placements/{booking_id}/payment", headers=auth,
              json={"amount_paise": 2500000, "method": "cash"})
    assert http.delete(f"/api/placements/{booking_id}", headers=auth).status_code == 200
    db.expire_all()
    assert db.query(models.AdPayment).filter(models.AdPayment.placement_id == booking_id).count() == 0, (
        "deleting a booking left its payment behind, pointing at nothing"
    )
    print("  ok  deleting a booking takes its payment record with it")

    print("ad payments: all checks passed")
finally:
    try:
        if db is not None:
            db.close()
        from backend.database import engine as _engine
        _engine.dispose()
    finally:
        admin.cursor().execute(f'DROP DATABASE IF EXISTS "{SCRATCH}"')
        admin.close()
