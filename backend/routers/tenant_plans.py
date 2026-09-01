"""The packages a tenant sells to its own clients.

Deliberately separate from `models.Plan`, which is what OLRAC bills the TENANT. One table
for both would let a tenant edit the plan they are billed on, and would put OLRAC's pricing
in front of their customers.

A booking COPIES a plan's price and duration at the moment it is created (see
routers/placements.create_placement). Nothing downstream reads through to this table for
money, so repricing a plan never rebills a campaign that was already sold.
"""
from fastapi import APIRouter, Depends, HTTPException

from .. import models, schemas
from ..tenancy import TenantScope, get_tenant_scope, require_tenant_roles

router = APIRouter()


@router.get("/", response_model=list[schemas.TenantPlanResponse])
def list_tenant_plans(
    include_inactive: bool = False,
    scope: TenantScope = Depends(get_tenant_scope),
):
    query = scope.query(models.TenantPlan)
    if not include_inactive:
        query = query.filter(models.TenantPlan.is_active.is_(True))
    return query.order_by(models.TenantPlan.price_paise).all()


@router.post("/", response_model=schemas.TenantPlanResponse, status_code=201)
def create_tenant_plan(
    payload: schemas.TenantPlanCreate,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    plan = models.TenantPlan(
        organization_id=scope.organization_id,
        **payload.model_dump(),
    )
    scope.db.add(plan)
    scope.db.commit()
    scope.db.refresh(plan)
    return plan


@router.get("/{plan_id}", response_model=schemas.TenantPlanResponse)
def get_tenant_plan(plan_id: int, scope: TenantScope = Depends(get_tenant_scope)):
    plan = scope.get(models.TenantPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.put("/{plan_id}", response_model=schemas.TenantPlanResponse)
def update_tenant_plan(
    plan_id: int,
    payload: schemas.TenantPlanUpdate,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    plan = scope.get(models.TenantPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(plan, field, value)
    scope.db.commit()
    scope.db.refresh(plan)
    return plan


@router.delete("/{plan_id}")
def delete_tenant_plan(
    plan_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    """Retire a plan, or delete it outright if nothing was ever sold on it.

    A plan that has bookings is deactivated rather than removed. The foreign key would
    survive the delete -- it is ON DELETE SET NULL -- but the report would then lose the
    plan name it prints, and a client asking "what did I buy?" is entitled to an answer
    after the tenant stops offering it.
    """
    plan = scope.get(models.TenantPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    sold = scope.db.query(models.AdPlacement).filter(
        models.AdPlacement.plan_id == plan.id
    ).count()
    if sold:
        plan.is_active = False
        scope.db.commit()
        return {"status": "retired", "bookings": sold}

    scope.db.delete(plan)
    scope.db.commit()
    return {"status": "deleted"}
