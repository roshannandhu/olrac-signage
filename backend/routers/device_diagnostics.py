"""What a screen can tell us about itself that nobody standing in front of it is there to read.

TVs are installed in venues, not next to whoever supports them. When one misbehaves in a way
only its own settings reveal -- an accessibility switch Android has locked, a permission
revoked, a launcher role lost -- the only way to find out was to send someone. The player now
reports that state here, and the latest report per screen is kept for an operator to read.

Stored as a SystemSetting row rather than a column: the report is diagnostic, its shape will
change as players learn to report more, and a schema migration per field would be the wrong
price for that.
"""
import json
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import database, models
from .screens import security, verify_device_auth

router = APIRouter()

# Generous for a flat map of flags and short strings, small enough that a misbehaving player
# cannot use this to write arbitrary blobs into the settings table.
MAX_REPORT_BYTES = 8_000


def diagnostics_key(screen_id: int) -> str:
    return f"device_diagnostics:{screen_id}"


class DiagnosticsReport(BaseModel):
    device_id: str
    report: Dict[str, Any]


@router.post("/diagnostics")
def report_diagnostics(
    body: DiagnosticsReport,
    db: Session = Depends(database.get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    screen = verify_device_auth(body.device_id, credentials, db)
    # Only a screen that proved itself with its device token. The legacy device-id-only path
    # would let anyone who knows an id overwrite what support reads about that screen.
    if not getattr(screen, "authenticated", False):
        raise HTTPException(status_code=403, detail="Diagnostics require a device token")

    payload = {"received_at": models.utcnow().isoformat(), "report": body.report}
    value = json.dumps(payload, sort_keys=True, default=str)
    if len(value.encode("utf-8")) > MAX_REPORT_BYTES:
        raise HTTPException(status_code=413, detail="Diagnostics report too large")

    key = diagnostics_key(screen.id)
    row = db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
    if row:
        row.value = value
        row.updated_at = models.utcnow()
    else:
        db.add(models.SystemSetting(key=key, value=value, description=f"Latest self-report from screen {screen.id}"))
    db.commit()
    return {"status": "ok"}
