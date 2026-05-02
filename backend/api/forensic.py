"""
Forensic Investigation API
Timeline analysis and incident investigation tools
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import json

from database import get_db, EmailAnalysis, User, Alert, TrustedRegistry, Organization
from auth.permissions import get_current_active_user, CurrentUser

router = APIRouter(tags=["forensic"])


@router.get("/sender-timeline")
async def get_sender_timeline(
    sender_email: str = Query(..., description="Sender email to investigate"),
    days_back: int = Query(365, ge=1, le=1095, description="Days to look back"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user),
):
    """
    Get all emails from a specific sender over time.
    Returns timeline with all communications.
    """
    start_date = datetime.utcnow() - timedelta(days=days_back)
    
    # Get all emails from this sender
    query = (
        select(EmailAnalysis)
        .where(
            and_(
                EmailAnalysis.from_address.ilike(f"%{sender_email}%"),
                EmailAnalysis.analyzed_at >= start_date
            )
        )
        .order_by(desc(EmailAnalysis.analyzed_at))
    )
    
    result = await db.execute(query)
    emails = result.scalars().all()
    
    timeline = []
    for email in emails:
        timeline.append({
            "id": email.id,
            "message_id": email.message_id,
            "from": email.from_address,
            "to": email.to_address,
            "subject": email.subject,
            "risk_score": email.risk_score,
            "status": email.status,
            "technical_score": email.technical_score,
            "linguistic_score": email.linguistic_score,
            "behavioral_score": email.behavioral_score,
            "contextual_score": email.contextual_score,
            "in_registry": email.in_registry,
            "trust_level": email.trust_level,
            "analyzed_at": email.analyzed_at.isoformat() if email.analyzed_at else None,
            "analysis_details": email.analysis_details,
        })
    
    # Calculate statistics
    stats = {
        "total_emails": len(timeline),
        "high_risk": sum(1 for e in timeline if e["risk_score"] >= 75),
        "medium_risk": sum(1 for e in timeline if 50 <= e["risk_score"] < 75),
        "safe": sum(1 for e in timeline if e["risk_score"] < 50),
        "unique_recipients": len(set(e["to"] for e in timeline)),
        "first_seen": timeline[-1]["analyzed_at"] if timeline else None,
        "last_seen": timeline[0]["analyzed_at"] if timeline else None,
    }
    
    return {
        "sender": sender_email,
        "timeline": timeline,
        "statistics": stats,
    }


@router.get("/recipient-network")
async def get_recipient_network(
    sender_email: str = Query(..., description="Sender email"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user),
):
    """
    Find all recipients who received emails from this sender
    and build connection graph.
    """
    # Get all emails from sender
    query = select(EmailAnalysis).where(
        EmailAnalysis.from_address.ilike(f"%{sender_email}%")
    )
    result = await db.execute(query)
    emails = result.scalars().all()
    
    # Build recipient network
    recipients = {}
    for email in emails:
        recipient = email.to_address
        if recipient not in recipients:
            recipients[recipient] = {
                "email": recipient,
                "count": 0,
                "first_contact": email.analyzed_at,
                "last_contact": email.analyzed_at,
                "risk_scores": [],
                "statuses": [],
            }
        
        recipients[recipient]["count"] += 1
        recipients[recipient]["risk_scores"].append(email.risk_score or 0)
        recipients[recipient]["statuses"].append(email.status)
        
        if email.analyzed_at and email.analyzed_at < recipients[recipient]["first_contact"]:
            recipients[recipient]["first_contact"] = email.analyzed_at
        if email.analyzed_at and email.analyzed_at > recipients[recipient]["last_contact"]:
            recipients[recipient]["last_contact"] = email.analyzed_at
    
    # Calculate network metrics
    network = []
    for email, data in recipients.items():
        avg_risk = sum(data["risk_scores"]) / len(data["risk_scores"]) if data["risk_scores"] else 0
        high_risk_count = sum(1 for s in data["statuses"] if s in ["danger", "warning"])
        
        network.append({
            "email": data["email"],
            "emails_received": data["count"],
            "average_risk_score": round(avg_risk, 2),
            "high_risk_count": high_risk_count,
            "first_contact": data["first_contact"].isoformat() if data["first_contact"] else None,
            "last_contact": data["last_contact"].isoformat() if data["last_contact"] else None,
        })
    
    # Sort by risk
    network.sort(key=lambda x: x["average_risk_score"], reverse=True)
    
    # Get user info for internal recipients
    user_query = select(User.email, User.full_name, User.department, User.organization_id).where(
        User.email.in_([r["email"] for r in network])
    )
    user_result = await db.execute(user_query)
    users = {u.email: {"full_name": u.full_name, "department": u.department} for u in user_result.scalars().all()}
    
    # Add user info to network
    for node in network:
        if node["email"] in users:
            node["user_name"] = users[node["email"]]["full_name"]
            node["department"] = users[node["email"]]["department"]
    
    return {
        "sender": sender_email,
        "total_recipients": len(network),
        "network": network,
        "high_risk_recipients": [n for n in network if n["average_risk_score"] >= 50],
    }


@router.get("/email-details/{email_id}")
async def get_email_forensic_details(
    email_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user),
):
    """
    Get detailed forensic information about a specific email.
    """
    query = select(EmailAnalysis).where(EmailAnalysis.id == email_id)
    result = await db.execute(query)
    email = result.scalars().first()
    
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Get related alerts
    alert_query = select(Alert).where(Alert.email_analysis_id == email_id)
    alert_result = await db.execute(alert_query)
    alerts = alert_result.scalars().all()
    
    # Get sender registry info
    sender_domain = email.from_address.split("@")[-1] if "@" in email.from_address else ""
    registry_query = select(TrustedRegistry).where(
        or_(
            TrustedRegistry.email_address == email.from_address,
            TrustedRegistry.domain == sender_domain
        )
    )
    registry_result = await db.execute(registry_query)
    registry_info = registry_result.scalars().first()
    
    return {
        "email": {
            "id": email.id,
            "message_id": email.message_id,
            "from": email.from_address,
            "to": email.to_address,
            "subject": email.subject,
            "body_preview": email.body_preview,
            "risk_score": email.risk_score,
            "status": email.status,
            "in_registry": email.in_registry,
            "trust_level": email.trust_level,
            "technical_score": email.technical_score,
            "linguistic_score": email.linguistic_score,
            "behavioral_score": email.behavioral_score,
            "contextual_score": email.contextual_score,
            "analysis_details": email.analysis_details,
            "body_text": email.body_text,
            "raw_headers": email.raw_headers,
            "analyzed_at": email.analyzed_at.isoformat() if email.analyzed_at else None,
        },
        "alerts": [
            {
                "id": a.id,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "title": a.title,
                "description": a.description,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in alerts
        ],
        "registry_info": {
            "is_registered": registry_info is not None,
            "organization_name": registry_info.organization_name if registry_info else None,
            "trust_level": registry_info.trust_level if registry_info else None,
            "is_verified": registry_info.is_verified if registry_info else None,
        } if registry_info or True else None,
    }


@router.post("/export-report")
async def export_forensic_report(
    sender_email: str = Query(...),
    format: str = Query("json", regex="^(json|pdf)$"),
    days_back: int = Query(365, ge=1, le=1095),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user),
):
    """
    Export comprehensive forensic report.
    """
    start_date = datetime.utcnow() - timedelta(days=days_back)
    
    # Get timeline data
    timeline_query = (
        select(EmailAnalysis)
        .where(
            and_(
                EmailAnalysis.from_address.ilike(f"%{sender_email}%"),
                EmailAnalysis.analyzed_at >= start_date
            )
        )
        .order_by(desc(EmailAnalysis.analyzed_at))
    )
    timeline_result = await db.execute(timeline_query)
    emails = timeline_result.scalars().all()
    
    # Build report
    report = {
        "report_type": "Forensic Email Analysis",
        "generated_at": datetime.utcnow().isoformat(),
        "investigator": current_user.email,
        "target_sender": sender_email,
        "time_range": f"{days_back} days",
        "summary": {
            "total_emails": len(emails),
            "high_risk_count": sum(1 for e in emails if (e.risk_score or 0) >= 75),
            "medium_risk_count": sum(1 for e in emails if 50 <= (e.risk_score or 0) < 75),
            "safe_count": sum(1 for e in emails if (e.risk_score or 0) < 50),
            "unique_recipients": len(set(e.to_address for e in emails)),
        },
        "timeline": [
            {
                "date": e.analyzed_at.isoformat() if e.analyzed_at else None,
                "to": e.to_address,
                "subject": e.subject,
                "risk_score": e.risk_score,
                "status": e.status,
            }
            for e in emails
        ],
        "recommendations": _generate_recommendations(emails),
    }
    
    if format == "json":
        return report
    
    # For PDF - return JSON with PDF flag (would need PDF library for actual PDF)
    return {
        "report": report,
        "format": "pdf",
        "note": "PDF generation requires additional library. JSON report provided.",
    }


def _generate_recommendations(emails) -> List[Dict[str, str]]:
    """Generate security recommendations based on analysis."""
    recommendations = []
    
    high_risk = [e for e in emails if (e.risk_score or 0) >= 75]
    if len(high_risk) > 5:
        recommendations.append({
            "severity": "critical",
            "title": "High Volume of Risky Emails",
            "description": f"{len(high_risk)} emails with risk score > 75 detected. Consider blocking sender.",
        })
    
    # Check for credential harvesting patterns
    subjects = [e.subject.lower() for e in emails if e.subject]
    if any("password" in s or "account" in s or "verify" in s for s in subjects):
        recommendations.append({
            "severity": "high",
            "title": "Credential Harvesting Attempt",
            "description": "Emails contain password/account related keywords. Likely credential phishing.",
        })
    
    # Check registry status
    not_in_registry = [e for e in emails if not e.in_registry]
    if len(not_in_registry) > len(emails) * 0.5:
        recommendations.append({
            "severity": "medium",
            "title": "Sender Not in Trusted Registry",
            "description": f"Only {len(emails) - len(not_in_registry)}/{len(emails)} emails from trusted senders.",
        })
    
    return recommendations


@router.get("/incident-timeline/{analysis_id}")
async def get_incident_timeline(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user),
):
    """
    Get full timeline for a specific incident/analysis.
    Shows all related emails and connections.
    """
    # Get the main analysis
    query = select(EmailAnalysis).where(EmailAnalysis.id == analysis_id)
    result = await db.execute(query)
    main_email = result.scalars().first()
    
    if not main_email:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Get all emails from same sender
    sender = main_email.from_address
    sender_query = (
        select(EmailAnalysis)
        .where(EmailAnalysis.from_address.ilike(f"%{sender}%"))
        .order_by(desc(EmailAnalysis.analyzed_at))
    )
    sender_result = await db.execute(sender_query)
    all_from_sender = sender_result.scalars().all()
    
    # Build incident timeline
    incident = {
        "main_email": {
            "id": main_email.id,
            "from": main_email.from_address,
            "to": main_email.to_address,
            "subject": main_email.subject,
            "risk_score": main_email.risk_score,
            "status": main_email.status,
            "analyzed_at": main_email.analyzed_at.isoformat() if main_email.analyzed_at else None,
        },
        "sender_history": {
            "total_emails": len(all_from_sender),
            "first_contact": all_from_sender[-1].analyzed_at.isoformat() if all_from_sender and all_from_sender[-1].analyzed_at else None,
            "last_contact": all_from_sender[0].analyzed_at.isoformat() if all_from_sender and all_from_sender[0].analyzed_at else None,
        },
        "timeline": [
            {
                "date": e.analyzed_at.isoformat() if e.analyzed_at else None,
                "event": "Email received",
                "recipient": e.to_address,
                "subject": e.subject,
                "risk": e.risk_score,
                "status": e.status,
            }
            for e in all_from_sender
        ],
    }
    
    return incident