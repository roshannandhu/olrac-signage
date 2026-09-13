"""Noticing that a paid window has closed.

The decision itself -- is this subscription still in force -- lives in `backend.billing`
next to `plan_features`, not here. `tenancy` consults it from inside a permission check and
the repositories import `tenancy`, so a service would put the data floor above the service
layer and break the layering contract in `.importlinter`. This module is only the sweep that
writes down what that decision already implies.
"""
import logging

from sqlalchemy.orm import Session

from .. import models
from ..billing import TERMINAL_SUBSCRIPTION_STATUSES, subscription_state

logger = logging.getLogger(__name__)


def expire_due_subscriptions(db: Session) -> int:
    """Mark every subscription whose window has closed. Returns how many moved.

    Idempotent -- it only moves a row that `subscription_state` already considers expired --
    so running it every thirty seconds costs one indexed query and no writes once the
    backlog is clear.
    """
    candidates = (
        db.query(models.Subscription)
        .filter(models.Subscription.status.notin_(sorted(TERMINAL_SUBSCRIPTION_STATUSES)))
        .filter(models.Subscription.current_period_end.isnot(None))
        .filter(models.Subscription.current_period_end <= models.utcnow())
        .all()
    )

    moved = 0
    for subscription in candidates:
        # Grace may still be running even though the period has closed; that is not expiry.
        if subscription_state(subscription) != "expired":
            continue
        # One subscription per transaction. Committing once at the end reads tidier and is
        # wrong: a single unwritable row rolls the session back and takes every expiry
        # already staged in that pass with it.
        try:
            subscription.status = "expired"
            db.commit()
            moved += 1
            logger.info(
                "Subscription for organisation %s expired (period ended %s)",
                subscription.organization_id,
                subscription.current_period_end,
            )
        except Exception:
            db.rollback()
            logger.exception(
                "Could not expire subscription for organisation %s",
                subscription.organization_id,
            )
    return moved
