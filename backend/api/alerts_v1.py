from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from typing import List

from database import Alert, get_db
from auth.permissions import get_current_active_user, CurrentUser

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])


def alert_to_dict(alert: Alert) -> dict:
    return {
        "id": alert.id,
        "email_analysis_id": alert.email_analysis_id,
        "alert_type": alert.alert_type,
        "severity": alert.severity,
        "title": alert.title,
        "description": alert.description,
        "message": alert.message,
        "recipient_email": alert.recipient_email,
        "sender_email": alert.sender_email,
        "action_taken": alert.action_taken,
        "status": alert.status,
        "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        "acknowledged_by": alert.acknowledged_by,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
    }


@router.get("/")
async def list_alerts(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: str | None = Query(None, description="OPEN/ACKNOWLEDGED/RESOLVED"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user),
):
    # Data isolation: admins see all, users see only their own
    if current_user.is_admin() or current_user.is_security_officer():
        query = select(Alert)
        count_query = select(func.count()).select_from(Alert)
    else:
        base_filter = Alert.user_id == current_user.id
        query = select(Alert).where(base_filter)
        count_query = select(func.count()).select_from(Alert).where(base_filter)

    if status_filter:
        query = query.where(Alert.status == status_filter.upper())
        count_query = count_query.where(Alert.status == status_filter.upper())

    query = query.order_by(Alert.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    items: List[Alert] = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    return {
        "data": [alert_to_dict(a) for a in items],
        "count": total,
    }


@router.get("/open")
async def list_open_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user),
):
    # Data isolation: admins see all open alerts, users see only their own
    if current_user.is_admin() or current_user.is_security_officer():
        result = await db.execute(
            select(Alert).where(Alert.status == "OPEN").order_by(Alert.created_at.desc())
        )
    else:
        result = await db.execute(
            select(Alert).where(
                Alert.status == "OPEN",
                Alert.user_id == current_user.id
            ).order_by(Alert.created_at.desc())
        )
    items = result.scalars().all()
    return [alert_to_dict(a) for a in items]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_alert(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user),
):
    required_fields = ["alert_type", "severity", "title", "recipient_email", "sender_email"]
    for f in required_fields:
        if f not in payload:
            raise HTTPException(status_code=400, detail=f"Field '{f}' is required")

    alert = Alert(
        user_id=current_user.id,  # Data isolation: assign to current user
        email_analysis_id=payload.get("email_analysis_id"),
        alert_type=payload["alert_type"],
        severity=payload["severity"],
        title=payload["title"],
        description=payload.get("description"),
        message=payload.get("message"),
        recipient_email=payload["recipient_email"],
        sender_email=payload["sender_email"],
        action_taken=payload.get("action_taken", "PENDING"),
        status=payload.get("status", "OPEN").upper(),
        acknowledged_at=None,
        acknowledged_by=None,
        created_at=datetime.utcnow(),
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    
    # Send WebSocket notification
    from websocket_integration import notify_alert_created
    alert_dict = alert_to_dict(alert)
    await notify_alert_created(alert_dict)
    
    return alert_dict


@router.patch("/{alert_id}")
async def update_alert(
    alert_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user),
):
    # BUG-14 fix: admins/security officers can access any alert, users only their own
    if current_user.is_admin() or current_user.is_security_officer():
        result = await db.execute(
            select(Alert).where(Alert.id == alert_id)
        )
    else:
        result = await db.execute(
            select(Alert).where(Alert.id == alert_id, Alert.user_id == current_user.id)
        )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    for field in [
        "alert_type",
        "severity",
        "title",
        "description",
        "message",
        "recipient_email",
        "sender_email",
        "action_taken",
        "status",
    ]:
        if field in payload and payload[field] is not None:
            setattr(alert, field, payload[field])

    await db.commit()
    await db.refresh(alert)
    return alert_to_dict(alert)


@router.post("/{alert_id}/ack")
async def acknowledge_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user),
):
    # BUG-14 fix: admins/security officers can acknowledge any alert
    if current_user.is_admin() or current_user.is_security_officer():
        result = await db.execute(
            select(Alert).where(Alert.id == alert_id)
        )
    else:
        result = await db.execute(
            select(Alert).where(Alert.id == alert_id, Alert.user_id == current_user.id)
        )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "ACKNOWLEDGED"
    alert.acknowledged_at = datetime.utcnow()
    alert.acknowledged_by = current_user.id

    await db.commit()
    await db.refresh(alert)
    return alert_to_dict(alert)
