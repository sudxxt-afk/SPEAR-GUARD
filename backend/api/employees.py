from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from database import get_db, User, EmailAnalysis, Organization, PhishingReport, MailAccount
from api.auth import get_current_user

router = APIRouter()

@router.get("/{user_id}/stats")
async def get_employee_stats(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Verify access (Admin or Security Officer of same Org)
    target_user = await db.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.role != "admin":
        if current_user.role != "security_officer":
            raise HTTPException(status_code=403, detail="Not authorized")
        if current_user.organization_id != target_user.organization_id:
            raise HTTPException(status_code=403, detail="Access to other organization denied")

    # 2. Base Query for Analysis
    stmt = select(EmailAnalysis).where(EmailAnalysis.user_id == user_id)
    result = await db.execute(stmt)
    analyses = result.scalars().all()

    # 3. Simple Stats
    total_emails = len(analyses)
    high_risk_count = sum(1 for a in analyses if a.risk_score >= 70)
    medium_risk_count = sum(1 for a in analyses if 40 <= a.risk_score < 70)
    low_risk_count = sum(1 for a in analyses if a.risk_score < 40)

    # 4. Top Senders
    senders_map = {}
    for a in analyses:
        if a.from_address not in senders_map:
            senders_map[a.from_address] = {"count": 0, "high_risk": 0}
        senders_map[a.from_address]["count"] += 1
        if a.risk_score >= 70:
            senders_map[a.from_address]["high_risk"] += 1
    
    top_senders = sorted(
        [{"email": k, **v} for k, v in senders_map.items()],
        key=lambda x: x["count"],
        reverse=True
    )[:5]

    # 5. Internal vs External
    org_domain = None
    if target_user.organization_id:
        org = await db.get(Organization, target_user.organization_id)
        if org and org.domain:
            org_domain = org.domain.lower()
    
    internal_count = 0
    external_count = 0
    for a in analyses:
        sender_domain = a.from_address.split('@')[-1].lower() if '@' in a.from_address else ''
        if org_domain and sender_domain.endswith(org_domain):
            internal_count += 1
        else:
            external_count += 1

    # 6. Trust Score Calculation
    # BUG-07 fix: high-risk emails → PENALIZE trust, phishing reports → BOOST trust.
    # Baseline 70: reflects average employee. Penalize heavily for receiving risky emails
    # (shows they're a target), reward for correctly reporting phishing (shows awareness).
    report_stmt = select(func.count(PhishingReport.id)).where(PhishingReport.reporter_id == user_id)
    reports_count = await db.scalar(report_stmt) or 0

    trust_score = 70 - (high_risk_count * 5) + (reports_count * 5)
    trust_score = max(0, min(100, trust_score))

    # 7. Recent Activity
    recent_activity = []
    sorted_analyses = sorted(analyses, key=lambda x: x.analyzed_at or datetime.min, reverse=True)[:10]
    for a in sorted_analyses:
        recent_activity.append({
            "id": a.id,
            "subject": a.subject,
            "from_address": a.from_address,
            "risk_score": a.risk_score,
            "analyzed_at": a.analyzed_at.isoformat() if a.analyzed_at else None
        })

    # 8. Activity Heatmap (By Hour)
    activity_by_hour = [0] * 24
    for a in analyses:
        if a.analyzed_at:
            activity_by_hour[a.analyzed_at.hour] += 1
            
    # 9. Mail Accounts
    accounts_stmt = select(MailAccount).where(MailAccount.user_id == user_id)
    accounts_res = await db.execute(accounts_stmt)
    mail_accounts = [
        {"email": acc.email, "provider": acc.provider, "is_active": acc.is_active} 
        for acc in accounts_res.scalars().all()
    ]

    # 10. Online Status (Mock for now, or use manager if importable)
    # Ideally import connection_manager, but circular import risk.
    # We will assume offline unless we can safely check.
    is_online = False
    try:
        from websocket_manager import connection_manager
        is_online = user_id in connection_manager.active_connections
    except ImportError:
        pass

    return {
        "user_info": {
            "full_name": target_user.full_name,
            "email": target_user.email,
            "role": target_user.role,
            "department": target_user.department,
            "is_online": is_online,
            "last_active": target_user.updated_at.isoformat() if target_user.updated_at else None
        },
        "stats": {
            "total_emails": total_emails,
            "high_risk": high_risk_count,
            "medium_risk": medium_risk_count,
            "trust_score": trust_score,
            "phishing_reports": reports_count,
            "internal_emails": internal_count,
            "external_emails": external_count
        },
        "top_senders": top_senders,
        "recent_activity": recent_activity,
        "activity_by_hour": activity_by_hour,
        "mail_accounts": mail_accounts
    }
