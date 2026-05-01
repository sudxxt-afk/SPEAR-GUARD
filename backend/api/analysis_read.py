from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from database import EmailAnalysis, get_db
from auth.permissions import get_current_active_user, CurrentUser

router = APIRouter(prefix="/api/v1/analysis", tags=["Analysis"])


def analysis_to_dict(item: EmailAnalysis) -> dict:
    return {
        "id": item.id,
        "sender_email": item.from_address,
        "recipient_email": item.to_address,
        "subject": item.subject,
        "body_preview": item.body_preview,
        "body_text": item.body_text,  # BUG-18 fix: model has body_text field
        "technical_score": item.technical_score,
        "linguistic_score": item.linguistic_score,
        "behavioral_score": item.behavioral_score,
        "contextual_score": item.contextual_score,
        "risk_score": item.risk_score,
        "decision": item.status or "PENDING",
        "analysis_details": item.analysis_details,
        "explanation": "",
        "has_attachments": False,
        "attachment_count": 0,
        "suspicious_urls": [],
        # BUG-04 fix: model has no created_at, only analyzed_at
        "created_at": item.analyzed_at,
        "analyzed_at": item.analyzed_at,
        "analyzed_by": item.user_id,
    }


@router.get("/")
async def list_analysis(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user),
):
    # Data isolation: 
    # - Admins/Security Officers can see all data
    # - Regular users see only their own analyses
    if current_user.is_admin() or current_user.is_security_officer():
        # Admin/Security Officer: no filter, see all
        query = (
            select(EmailAnalysis)
            .order_by(EmailAnalysis.analyzed_at.desc())
            .offset(offset)
            .limit(limit)
        )
        count_query = select(func.count()).select_from(EmailAnalysis)
    else:
        # Regular user: filter by user_id
        base_filter = EmailAnalysis.user_id == current_user.id
        query = (
            select(EmailAnalysis)
            .where(base_filter)
            .order_by(EmailAnalysis.analyzed_at.desc())
            .offset(offset)
            .limit(limit)
        )
        count_query = select(func.count()).select_from(EmailAnalysis).where(base_filter)

    result = await db.execute(query)
    items: List[EmailAnalysis] = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    return {
        "data": [analysis_to_dict(i) for i in items],
        "count": total,
    }


@router.get("/{analysis_id}")
async def get_analysis(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user),
):
    # Data isolation: admins can access any analysis, users only their own
    if current_user.is_admin() or current_user.is_security_officer():
        result = await db.execute(
            select(EmailAnalysis).where(EmailAnalysis.id == analysis_id)
        )
    else:
        result = await db.execute(
            select(EmailAnalysis).where(
                EmailAnalysis.id == analysis_id,
                EmailAnalysis.user_id == current_user.id
            )
        )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis_to_dict(item)
