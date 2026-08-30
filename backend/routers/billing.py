import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import func

from .. import models, schemas
from ..billing import plan_features
from ..payments import get_payment_provider
from ..tenancy import TenantScope, get_tenant_scope


router = APIRouter()


def serialize_plan(plan: models.Plan) -> schemas.PlanResponse:
    return schemas.PlanResponse(
        id=plan.id,
        name=plan.name,
        slug=plan.slug,
        monthly_price_paise=plan.monthly_price_paise,
        yearly_price_paise=plan.yearly_price_paise,
        max_screens=plan.max_screens,
        max_storage_bytes=plan.max_storage_bytes,
        feature_flags=plan_features(plan),
    )


def serialize_subscription(subscription: models.Subscription) -> schemas.SubscriptionResponse:
    return schemas.SubscriptionResponse.model_validate(subscription, from_attributes=True)


@router.get("/plans", response_model=list[schemas.PlanResponse])
def list_plans(scope: TenantScope = Depends(get_tenant_scope)):
    return [
        serialize_plan(plan)
        for plan in scope.db.query(models.Plan)
        .filter(models.Plan.is_active.is_(True))
        .order_by(models.Plan.monthly_price_paise)
        .all()
    ]


@router.get("/summary", response_model=schemas.BillingSummaryResponse)
def billing_summary(scope: TenantScope = Depends(get_tenant_scope)):
    from ..billing import ensure_billing_catalog
    organization = scope.db.query(models.Organization).filter(
        models.Organization.id == scope.organization_id
    ).one()
    plan_id = organization.plan_id or 1
    plan = scope.db.query(models.Plan).filter(models.Plan.id == plan_id).first()
    if not plan:
        ensure_billing_catalog(scope.db)
        scope.db.commit()
        plan = scope.db.query(models.Plan).filter(models.Plan.id == plan_id).first() or scope.db.query(models.Plan).order_by(models.Plan.id.asc()).first()
    
    subscription = scope.db.query(models.Subscription).filter(
        models.Subscription.organization_id == scope.organization_id
    ).first()
    if not subscription and plan:
        subscription = models.Subscription(
            organization_id=scope.organization_id,
            plan_id=plan.id,
            status="active",
            billing_period="monthly",
        )
        scope.db.add(subscription)
        scope.db.commit()
        scope.db.refresh(subscription)
    storage_used = scope.query(models.Content).with_entities(
        func.coalesce(func.sum(models.Content.file_size_bytes), 0)
    ).scalar()
    screens_used = scope.query(models.Screen).filter(
        models.Screen.status != "waiting_pairing"
    ).count()
    return schemas.BillingSummaryResponse(
        plan=serialize_plan(plan),
        subscription=serialize_subscription(subscription),
        screens_used=screens_used,
        storage_used_bytes=storage_used,
        is_read_only=scope.is_read_only(),
    )


@router.post("/checkout", response_model=schemas.CheckoutResponse)
def create_checkout(payload: schemas.CheckoutRequest, scope: TenantScope = Depends(get_tenant_scope)):
    if scope.user.role != "owner":
        raise HTTPException(status_code=403, detail="Only an organization owner can change billing")
    plan = scope.db.query(models.Plan).filter(
        models.Plan.id == payload.plan_id,
        models.Plan.is_active.is_(True),
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    organization = scope.db.query(models.Organization).filter(
        models.Organization.id == scope.organization_id
    ).one()
    subscription = scope.db.query(models.Subscription).filter(
        models.Subscription.organization_id == scope.organization_id
    ).one()
    amount = plan.monthly_price_paise if payload.billing_period == "monthly" else plan.yearly_price_paise
    if amount == 0:
        organization.plan_id = plan.id
        organization.storage_quota_bytes = plan.max_storage_bytes
        subscription.plan_id = plan.id
        subscription.status = "active"
        subscription.billing_period = payload.billing_period
        subscription.provider = None
        subscription.provider_subscription_id = None
        subscription.grace_period_end = None
        scope.db.commit()
        return schemas.CheckoutResponse(
            provider="internal",
            provider_subscription_id=f"free-{scope.organization_id}",
            checkout_url="/dashboard/billing?updated=1",
        )

    provider_name = os.getenv("PAYMENT_PROVIDER", "razorpay").lower()
    env_name = f"RAZORPAY_{plan.slug.upper().replace('-', '_')}_{payload.billing_period.upper()}_PLAN_ID"
    provider_plan_id = os.getenv(env_name)
    if provider_name == "mock":
        provider_plan_id = provider_plan_id or f"plan_mock_{plan.slug}_{payload.billing_period}"
    if not provider_plan_id:
        raise HTTPException(status_code=503, detail=f"Billing plan is not configured ({env_name})")
    try:
        checkout = get_payment_provider().create_subscription(
            provider_plan_id=provider_plan_id,
            billing_period=payload.billing_period,
            organization_id=scope.organization_id,
            local_plan_id=plan.id,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    subscription.plan_id = plan.id
    subscription.status = "pending"
    subscription.billing_period = payload.billing_period
    subscription.provider = provider_name
    subscription.provider_subscription_id = checkout.provider_subscription_id
    subscription.updated_at = models.utcnow()
    scope.db.commit()
    return schemas.CheckoutResponse(
        provider=provider_name,
        provider_subscription_id=checkout.provider_subscription_id,
        checkout_url=checkout.checkout_url,
    )


@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
    x_razorpay_event_id: str | None = Header(default=None),
):
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(status_code=503, detail="RAZORPAY_WEBHOOK_SECRET is not configured")
    raw_body = await request.body()
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    if not x_razorpay_signature or not hmac.compare_digest(expected, x_razorpay_signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    if not x_razorpay_event_id:
        raise HTTPException(status_code=400, detail="Missing X-Razorpay-Event-Id")

    # Webhooks are unauthenticated by design; use the application's database
    # factory after signature verification instead of a tenant dependency.
    from .. import database

    db = database.SessionLocal()
    try:
        if db.query(models.WebhookEvent).filter(
            models.WebhookEvent.provider_event_id == x_razorpay_event_id
        ).first():
            return {"status": "duplicate"}
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc
        event_type = payload.get("event", "")
        entity = payload.get("payload", {}).get("subscription", {}).get("entity", {})
        provider_subscription_id = entity.get("id")
        subscription = db.query(models.Subscription).filter(
            models.Subscription.provider_subscription_id == provider_subscription_id
        ).first()
        db.add(
            models.WebhookEvent(
                provider="razorpay",
                provider_event_id=x_razorpay_event_id,
                event_type=event_type or "unknown",
            )
        )
        if subscription:
            active_events = {
                "subscription.authenticated",
                "subscription.activated",
                "subscription.charged",
                "subscription.resumed",
            }
            failure_events = {"subscription.pending", "subscription.halted"}
            read_only_events = {
                "subscription.cancelled",
                "subscription.completed",
                "subscription.paused",
            }
            if event_type in active_events:
                subscription.status = "active"
                subscription.grace_period_end = None
                subscription.current_period_start = timestamp_to_datetime(entity.get("current_start"))
                subscription.current_period_end = timestamp_to_datetime(entity.get("current_end"))
                subscription.organization.plan_id = subscription.plan_id
                subscription.organization.storage_quota_bytes = subscription.plan.max_storage_bytes
            elif event_type in failure_events:
                grace_days = max(1, min(int(os.getenv("BILLING_GRACE_DAYS", "7")), 30))
                subscription.status = "grace"
                subscription.grace_period_end = models.utcnow() + timedelta(days=grace_days)
            elif event_type in read_only_events:
                subscription.status = "read_only"
                subscription.grace_period_end = None
            subscription.updated_at = models.utcnow()
        db.commit()
        return {"status": "ok"}
    finally:
        db.close()


def timestamp_to_datetime(value) -> datetime | None:
    try:
        return datetime.utcfromtimestamp(int(value)) if value is not None else None
    except (TypeError, ValueError, OSError):
        return None
