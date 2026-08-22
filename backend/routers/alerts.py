from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import models, schemas
from ..tenancy import TenantScope, get_tenant_scope, require_tenant_roles

router = APIRouter()


def serialize(alert: models.Alert) -> schemas.AlertResponse:
    return schemas.AlertResponse.model_validate(alert)


@router.get("/", response_model=list[schemas.AlertResponse])
def list_alerts(
    scope: TenantScope = Depends(get_tenant_scope),
    include_resolved: bool = Query(False),
    limit: int = Query(200, ge=1, le=1000),
):
    """Open alerts, newest first. Resolved ones only when asked for.

    The default is deliberately "what is wrong now": an operator opening this wants the
    list to be actionable, and a history that never shrinks trains people to ignore it.
    """
    query = scope.query(models.Alert)
    if not include_resolved:
        query = query.filter(models.Alert.resolved_at.is_(None))
    else:
        # A week is enough to answer "what happened overnight" without loading months.
        cutoff = models.utcnow() - timedelta(days=7)
        query = query.filter(
            (models.Alert.resolved_at.is_(None)) | (models.Alert.raised_at >= cutoff)
        )
    return [
        serialize(alert)
        for alert in query.order_by(models.Alert.raised_at.desc()).limit(limit).all()
    ]


@router.post("/{alert_id}/acknowledge", response_model=schemas.AlertResponse)
def acknowledge_alert(
    alert_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    """Mark an alert as picked up, without claiming the underlying fault is fixed.

    Acknowledging and resolving are separate on purpose. Only the reconciler resolves, by
    observing that the condition stopped being true -- a person clicking a button is saying
    "I have seen this and I am dealing with it", which is a different fact and must not
    silence the alert if the screen is still down.
    """
    alert = scope.get(models.Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert.acknowledged_at is None:
        alert.acknowledged_at = models.utcnow()
        alert.acknowledged_by = scope.user.id
        scope.db.commit()
        scope.db.refresh(alert)
    return serialize(alert)


@router.get("/summary", response_model=schemas.AlertSummaryResponse)
def alert_summary(scope: TenantScope = Depends(get_tenant_scope)):
    """Counts for the navigation badge, so the header does not fetch the whole list."""
    open_alerts = scope.query(models.Alert).filter(
        models.Alert.resolved_at.is_(None)
    ).all()
    return schemas.AlertSummaryResponse(
        total=len(open_alerts),
        critical=sum(1 for a in open_alerts if a.severity == "critical"),
        warning=sum(1 for a in open_alerts if a.severity == "warning"),
        unacknowledged=sum(1 for a in open_alerts if a.acknowledged_at is None),
    )
