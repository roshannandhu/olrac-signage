import json

from sqlalchemy.orm import Session

from . import models


DEFAULT_PLANS = (
    {
        "name": "Free",
        "slug": "free",
        "monthly_price_paise": 0,
        "yearly_price_paise": 0,
        "duration_days": 30,
        "max_screens": 5,
        "max_clients": 3,
        "max_storage_bytes": 10 * 1024 * 1024 * 1024,
        "features": {"scheduling": True},
    },
    {
        "name": "Starter",
        "slug": "starter",
        "monthly_price_paise": 99_900,
        "yearly_price_paise": 999_000,
        "duration_days": 30,
        "max_screens": 10,
        "max_clients": 10,
        "max_storage_bytes": 25 * 1024 * 1024 * 1024,
        "features": {"scheduling": True, "transitions": True},
    },
    {
        "name": "Business",
        "slug": "business",
        "monthly_price_paise": 299_900,
        "yearly_price_paise": 2_999_000,
        "duration_days": 30,
        "max_screens": 50,
        "max_clients": 50,
        "max_storage_bytes": 100 * 1024 * 1024 * 1024,
        "features": {"scheduling": True, "transitions": True, "priority_support": True, "emergency_alert": True},
    },
)


def ensure_billing_catalog(db: Session) -> None:
    by_slug = {plan.slug: plan for plan in db.query(models.Plan).all()}
    for payload in DEFAULT_PLANS:
        if payload["slug"] in by_slug:
            continue
        db.add(
            models.Plan(
                name=payload["name"],
                slug=payload["slug"],
                monthly_price_paise=payload["monthly_price_paise"],
                yearly_price_paise=payload["yearly_price_paise"],
                # The storefront charges this once for `duration_days` of access; seed it
                # from the monthly figure so a fresh install is immediately sellable.
                price_paise=payload["monthly_price_paise"],
                duration_days=payload["duration_days"],
                max_screens=payload["max_screens"],
                max_clients=payload["max_clients"],
                max_storage_bytes=payload["max_storage_bytes"],
                feature_flags_json=json.dumps(payload["features"], sort_keys=True),
                is_active=True,
            )
        )
    db.flush()

    free_plan = db.query(models.Plan).filter(models.Plan.slug == "free").one()
    for organization in db.query(models.Organization).all():
        if organization.plan_id is None:
            organization.plan_id = free_plan.id
            organization.storage_quota_bytes = free_plan.max_storage_bytes
        if organization.subscription is None:
            db.add(
                models.Subscription(
                    organization_id=organization.id,
                    plan_id=organization.plan_id,
                    status="active",
                    billing_period="monthly",
                )
            )
    db.commit()


def plan_features(plan: models.Plan) -> dict[str, bool]:
    try:
        value = json.loads(plan.feature_flags_json or "{}")
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}
