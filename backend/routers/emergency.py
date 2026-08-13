import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import database, models, schemas
from ..tenancy import TenantScope, require_tenant_roles

router = APIRouter()

class BroadcastRequest(BaseModel):
    target_type: str # 'all', 'group', 'screen'
    target_id: int | None = None
    playlist_id: int

@router.get("/active")
def get_active_broadcasts(
    tenant: TenantScope = Depends(require_tenant_roles("owner", "editor", "viewer")),
    db: Session = Depends(database.get_db)
):
    broadcasts = db.query(models.EmergencyBroadcast).filter(
        models.EmergencyBroadcast.organization_id == tenant.organization_id,
        models.EmergencyBroadcast.is_active == True
    ).all()
    return [
        {
            "id": b.id,
            "target_type": b.target_type,
            "target_id": b.target_id,
            "playlist_id": b.playlist_id,
            "updated_at": b.updated_at
        } for b in broadcasts
    ]

@router.post("/broadcast")
async def trigger_emergency_broadcast(
    req: BroadcastRequest,
    tenant: TenantScope = Depends(require_tenant_roles("owner", "editor")),
    db: Session = Depends(database.get_db)
):
    if req.target_type not in ("all", "group", "screen"):
        raise HTTPException(status_code=400, detail="Invalid target_type")
        
    broadcast = db.query(models.EmergencyBroadcast).filter(
        models.EmergencyBroadcast.organization_id == tenant.organization_id,
        models.EmergencyBroadcast.target_type == req.target_type,
        models.EmergencyBroadcast.target_id == req.target_id,
        models.EmergencyBroadcast.is_active == True
    ).first()
    
    if broadcast:
        broadcast.playlist_id = req.playlist_id
        broadcast.updated_at = models.utcnow()
    else:
        broadcast = models.EmergencyBroadcast(
            organization_id=tenant.organization_id,
            target_type=req.target_type,
            target_id=req.target_id,
            playlist_id=req.playlist_id,
            is_active=True
        )
        db.add(broadcast)
        
    db.commit()
    
    # Publish to Redis
    try:
        redis = database.get_redis()
        msg = {"type": "emergency_override", "playlist_id": req.playlist_id}
        if req.target_type == "all":
            await redis.publish(f"org:{tenant.organization_id}", json.dumps(msg))
        elif req.target_type == "group":
            await redis.publish(f"group:{req.target_id}", json.dumps(msg))
        elif req.target_type == "screen":
            await redis.publish(f"screen:{req.target_id}", json.dumps(msg))
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to publish to redis: {e}")
        
    return {"status": "ok", "message": "Broadcast triggered"}

@router.post("/cancel")
async def cancel_emergency_broadcast(
    req: BroadcastRequest,
    tenant: TenantScope = Depends(require_tenant_roles("owner", "editor")),
    db: Session = Depends(database.get_db)
):
    broadcast = db.query(models.EmergencyBroadcast).filter(
        models.EmergencyBroadcast.organization_id == tenant.organization_id,
        models.EmergencyBroadcast.target_type == req.target_type,
        models.EmergencyBroadcast.target_id == req.target_id,
        models.EmergencyBroadcast.is_active == True
    ).first()
    
    if broadcast:
        broadcast.is_active = False
        db.commit()
        
    # Publish to Redis to tell TVs to reload normal playlist
    try:
        redis = database.get_redis()
        msg = {"type": "emergency_cancel"}
        if req.target_type == "all":
            await redis.publish(f"org:{tenant.organization_id}", json.dumps(msg))
        elif req.target_type == "group":
            await redis.publish(f"group:{req.target_id}", json.dumps(msg))
        elif req.target_type == "screen":
            await redis.publish(f"screen:{req.target_id}", json.dumps(msg))
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to publish to redis: {e}")
        
    return {"status": "ok", "message": "Broadcast cancelled"}
