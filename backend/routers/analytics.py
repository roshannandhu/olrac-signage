import csv
from datetime import datetime, timedelta, timezone
from io import BytesIO, StringIO
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from ..database import get_db
from ..tenancy import TenantScope, require_tenant_roles
from ..models import Campaign, PlayLogHourlyRollup, Screen

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/campaigns")
def list_campaigns(
    tenant: TenantScope = Depends(require_tenant_roles("owner", "editor", "viewer")),
    db: Session = Depends(get_db),
):
    campaigns = db.query(Campaign).filter(Campaign.organization_id == tenant.organization_id).all()
    return [{"id": c.id, "name": c.name} for c in campaigns]


@router.get("/campaigns/{campaign_id}")
def get_campaign_info(
    campaign_id: int,
    tenant: TenantScope = Depends(require_tenant_roles("owner", "editor", "viewer")),
    db: Session = Depends(get_db),
):
    campaign = db.query(Campaign).filter(
        Campaign.organization_id == tenant.organization_id,
        Campaign.id == campaign_id
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # To get currently playing / online / offline, we look at screens assigned to this campaign.
    # We resolve assigned screens via effective_playlist_id matching a playlist in this campaign.
    screens = db.query(Screen).filter(Screen.organization_id == tenant.organization_id).all()
    
    # Pre-fetch playlists belonging to this campaign
    campaign_playlist_ids = {p.id for p in campaign.playlists}
    
    assigned_screens = [s for s in screens if s.effective_playlist_id in campaign_playlist_ids]
    
    online = sum(1 for s in assigned_screens if s.status == "online")
    offline = sum(1 for s in assigned_screens if s.status == "offline")
    playing = sum(1 for s in assigned_screens if s.playback_state == "playing")

    return {
        "id": campaign.id,
        "name": campaign.name,
        "assigned_screens": len(assigned_screens),
        "online": online,
        "offline": offline,
        "currently_playing": playing,
    }


@router.get("/campaigns/{campaign_id}/stats")
def get_campaign_stats(
    campaign_id: int,
    tenant: TenantScope = Depends(require_tenant_roles("owner", "editor", "viewer")),
    db: Session = Depends(get_db),
):
    # Tenant scoping validation
    campaign = db.query(Campaign).filter(
        Campaign.organization_id == tenant.organization_id,
        Campaign.id == campaign_id
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    week_start = today_start - timedelta(days=today_start.weekday())

    def get_period_stats(start_time, end_time=None):
        query = db.query(
            func.sum(PlayLogHourlyRollup.total_plays),
            func.sum(PlayLogHourlyRollup.completed_plays),
            func.sum(PlayLogHourlyRollup.error_plays)
        ).filter(
            PlayLogHourlyRollup.organization_id == tenant.organization_id,
            PlayLogHourlyRollup.campaign_id == campaign_id,
            PlayLogHourlyRollup.date_hour >= start_time
        )
        if end_time:
            query = query.filter(PlayLogHourlyRollup.date_hour < end_time)
        return query.first()

    today = get_period_stats(today_start)
    yesterday = get_period_stats(yesterday_start, today_start)
    week = get_period_stats(week_start)
    lifetime = db.query(
        func.sum(PlayLogHourlyRollup.total_plays),
        func.sum(PlayLogHourlyRollup.completed_plays),
        func.sum(PlayLogHourlyRollup.error_plays)
    ).filter(
        PlayLogHourlyRollup.organization_id == tenant.organization_id,
        PlayLogHourlyRollup.campaign_id == campaign_id
    ).first()

    def format_stats(row):
        total = row[0] or 0
        completed = row[1] or 0
        error = row[2] or 0
        success_pct = (completed / total * 100) if total > 0 else 0
        return {
            "total_plays": total,
            "success_percent": round(success_pct, 1)
        }

    return {
        "today": format_stats(today),
        "yesterday": format_stats(yesterday),
        "week": format_stats(week),
        "lifetime": format_stats(lifetime)
    }


@router.get("/campaigns/{campaign_id}/timeseries")
def get_campaign_timeseries(
    campaign_id: int,
    tenant: TenantScope = Depends(require_tenant_roles("owner", "editor", "viewer")),
    db: Session = Depends(get_db),
):
    campaign = db.query(Campaign).filter(
        Campaign.organization_id == tenant.organization_id,
        Campaign.id == campaign_id
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Get last 7 days grouped by day
    rows = db.query(
        func.date_trunc('day', PlayLogHourlyRollup.date_hour).label('day'),
        func.sum(PlayLogHourlyRollup.total_plays).label('total'),
        func.sum(PlayLogHourlyRollup.completed_plays).label('completed')
    ).filter(
        PlayLogHourlyRollup.organization_id == tenant.organization_id,
        PlayLogHourlyRollup.campaign_id == campaign_id,
        PlayLogHourlyRollup.date_hour >= datetime.now(timezone.utc) - timedelta(days=7)
    ).group_by(
        func.date_trunc('day', PlayLogHourlyRollup.date_hour)
    ).order_by('day').all()

    return [
        {
            "date": row.day.strftime("%Y-%m-%d"),
            "total_plays": row.total,
            "completed_plays": row.completed
        }
        for row in rows
    ]


@router.get("/campaigns/{campaign_id}/export")
def export_campaign_report(
    campaign_id: int,
    format: str = "csv",
    tenant: TenantScope = Depends(require_tenant_roles("owner", "editor", "viewer")),
    db: Session = Depends(get_db),
):
    campaign = db.query(Campaign).filter(
        Campaign.organization_id == tenant.organization_id,
        Campaign.id == campaign_id
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    rows = db.query(
        PlayLogHourlyRollup.date_hour,
        Screen.name.label('screen_name'),
        func.sum(PlayLogHourlyRollup.total_plays).label('total_plays'),
        func.sum(PlayLogHourlyRollup.completed_plays).label('completed_plays'),
        func.sum(PlayLogHourlyRollup.error_plays).label('error_plays')
    ).join(
        Screen, Screen.id == PlayLogHourlyRollup.screen_id
    ).filter(
        PlayLogHourlyRollup.organization_id == tenant.organization_id,
        PlayLogHourlyRollup.campaign_id == campaign_id
    ).group_by(
        PlayLogHourlyRollup.date_hour, Screen.name
    ).order_by(PlayLogHourlyRollup.date_hour.desc()).all()

    filename = f"campaign_{campaign_id}_report.{format}"
    
    if format == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Date/Hour", "Screen", "Total Plays", "Completed Plays", "Error Plays"])
        for row in rows:
            writer.writerow([row.date_hour.strftime("%Y-%m-%d %H:00"), row.screen_name, row.total_plays, row.completed_plays, row.error_plays])
        
        output.seek(0)
        return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}"})
    
    elif format == "excel":
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Analytics"
        ws.append(["Date/Hour", "Screen", "Total Plays", "Completed Plays", "Error Plays"])
        for row in rows:
            ws.append([row.date_hour.strftime("%Y-%m-%d %H:00"), row.screen_name, row.total_plays, row.completed_plays, row.error_plays])
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return StreamingResponse(iter([output.getvalue()]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={filename}"})
    
    elif format == "pdf":
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
        
        output = BytesIO()
        doc = SimpleDocTemplate(output, pagesize=letter)
        
        data = [["Date/Hour", "Screen", "Total Plays", "Completed Plays", "Error Plays"]]
        for row in rows:
            data.append([row.date_hour.strftime("%Y-%m-%d %H:00"), row.screen_name, str(row.total_plays), str(row.completed_plays), str(row.error_plays)])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        doc.build([table])
        output.seek(0)
        return StreamingResponse(iter([output.getvalue()]), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={filename}"})
    
    else:
        raise HTTPException(status_code=400, detail="Invalid format")
