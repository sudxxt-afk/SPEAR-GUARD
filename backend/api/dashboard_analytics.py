"""
Dashboard Analytics API endpoints
Provides data for visualization components
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, case
from datetime import datetime, timedelta
from typing import List, Optional
from database import get_db, EmailAnalysis, Alert, TrustedRegistry, User
from auth.permissions import get_current_active_user, CurrentUser

router = APIRouter(tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_summary_stats(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user),
):
    """
    Get summary statistics for the dashboard
    """
    # Data isolation: admins see all, users see only their own
    is_privileged = current_user.is_admin() or current_user.is_security_officer()
    
    if is_privileged:
        # Admins see all data
        total_emails_query = select(func.count(EmailAnalysis.id))
        suspicious_emails_query = select(func.count(EmailAnalysis.id)).where(
            EmailAnalysis.risk_score >= 50
        )
        open_alerts_query = select(func.count(Alert.id)).where(Alert.status == 'OPEN')
    else:
        # Regular users see only their own data
        user_filter = EmailAnalysis.user_id == current_user.id
        alert_filter = Alert.user_id == current_user.id
        
        total_emails_query = select(func.count(EmailAnalysis.id)).where(user_filter)
        suspicious_emails_query = select(func.count(EmailAnalysis.id)).where(
            user_filter, EmailAnalysis.risk_score >= 50
        )
        open_alerts_query = select(func.count(Alert.id)).where(
            alert_filter, Alert.status == 'OPEN'
        )
    
    # Registry size (global for now)
    registry_size_query = select(func.count(TrustedRegistry.id)).where(TrustedRegistry.is_active == True)
    
    total_emails = (await db.execute(total_emails_query)).scalar() or 0
    suspicious_emails = (await db.execute(suspicious_emails_query)).scalar() or 0
    open_alerts = (await db.execute(open_alerts_query)).scalar() or 0
    registry_size = (await db.execute(registry_size_query)).scalar() or 0
    
    return {
        "totalEmails": total_emails,
        "suspiciousEmails": suspicious_emails,
        "alertsOpen": open_alerts,
        "registrySize": registry_size,
        "lastAnalysis": datetime.utcnow().isoformat(),
        "riskTrend": []
    }


@router.get("/threat-trend")
async def get_threat_trend(
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user),
):
    """
    Get threat trend data for the specified number of days
    Returns daily counts of threats, blocked, and quarantined emails
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # BUG-11 + BUG-24 fix: admins see all, SO sees org-wide, users see own only
    is_privileged = current_user.is_admin() or current_user.is_security_officer()

    # Build base conditions
    base_conditions = [
        EmailAnalysis.analyzed_at >= start_date,
        EmailAnalysis.analyzed_at <= end_date,
        EmailAnalysis.risk_score >= 25  # Only threats
    ]

    if is_privileged:
        if not current_user.is_admin() and current_user.organization_id:
            base_conditions.append(
                EmailAnalysis.user_id.in_(
                    select(User.id).where(User.organization_id == current_user.organization_id)
                )
            )
    else:
        base_conditions.append(EmailAnalysis.user_id == current_user.id)

    # Query for daily threat counts
    query = select(
        func.date(EmailAnalysis.analyzed_at).label('date'),
        func.count(EmailAnalysis.id).label('threats'),
        func.sum(
            case(
                (EmailAnalysis.status == 'blocked', 1),
                else_=0
            )
        ).label('blocked'),
        func.sum(
            case(
                (EmailAnalysis.status == 'quarantine', 1),
                else_=0
            )
        ).label('quarantined'),
    ).where(
        and_(*base_conditions)
    ).group_by(
        func.date(EmailAnalysis.analyzed_at)
    ).order_by(
        func.date(EmailAnalysis.analyzed_at)
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    # Format data
    data = []
    for row in rows:
        data.append({
            "date": row.date.strftime('%d.%m') if row.date else '',
            "full_date": row.date.strftime('%Y-%m-%d') if row.date else '',
            "threats": int(row.threats or 0),
            "blocked": int(row.blocked or 0),
            "quarantined": int(row.quarantined or 0),
        })
    
    return {"data": data, "period": f"{days} days"}


@router.get("/attack-map")
async def get_attack_map(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user),
):
    """
    Get geographic distribution of attacks
    Returns attack points with coordinates and severity
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    # BUG-11 fix: admins see all data, regular users see only their own
    is_privileged = current_user.is_admin() or current_user.is_security_officer()

    base_conditions = [
        EmailAnalysis.analyzed_at >= cutoff_time,
        EmailAnalysis.risk_score >= 25
    ]

    if is_privileged:
        # Admins/security officers: scope to their own organization if not admin
        if not current_user.is_admin() and current_user.organization_id:
            base_conditions.append(
                EmailAnalysis.user_id.in_(
                    select(User.id).where(User.organization_id == current_user.organization_id)
                )
            )
    else:
        # Regular users: their own data only
        base_conditions.append(EmailAnalysis.user_id == current_user.id)

    # Query for recent high-risk emails with geographic data
    query = select(
        EmailAnalysis.id,
        EmailAnalysis.from_address,
        EmailAnalysis.risk_score,
        EmailAnalysis.analyzed_at,
        case(
            (EmailAnalysis.risk_score >= 75, 'CRITICAL'),
            (EmailAnalysis.risk_score >= 50, 'HIGH'),
            (EmailAnalysis.risk_score >= 25, 'MEDIUM'),
            else_='LOW'
        ).label('severity')
    ).where(
        and_(*base_conditions)
    ).order_by(
        desc(EmailAnalysis.risk_score)
    ).limit(50)
    
    result = await db.execute(query)
    rows = result.all()
    
    # Mock geographic mapping (in production, use GeoIP database)
    geo_mapping = {
        '.ru': {'city': 'Moscow', 'country': 'Russia', 'lat': 55.7558, 'lng': 37.6173},
        '.cn': {'city': 'Beijing', 'country': 'China', 'lat': 39.9042, 'lng': 116.4074},
        '.uk': {'city': 'London', 'country': 'UK', 'lat': 51.5074, 'lng': -0.1278},
        '.com': {'city': 'New York', 'country': 'USA', 'lat': 40.7128, 'lng': -74.0060},
        '.jp': {'city': 'Tokyo', 'country': 'Japan', 'lat': 35.6762, 'lng': 139.6503},
        '.de': {'city': 'Berlin', 'country': 'Germany', 'lat': 52.5200, 'lng': 13.4050},
        '.fr': {'city': 'Paris', 'country': 'France', 'lat': 48.8566, 'lng': 2.3522},
    }
    
    # Group by location
    location_counts = {}
    for row in rows:
        # Determine location based on email domain
        domain = row.from_address.split('@')[-1] if '@' in row.from_address else ''
        tld = '.' + domain.split('.')[-1] if '.' in domain else '.com'
        
        geo = geo_mapping.get(tld, geo_mapping['.com'])
        key = f"{geo['city']},{geo['country']}"
        
        if key not in location_counts:
            location_counts[key] = {
                'id': len(location_counts) + 1,
                'city': geo['city'],
                'country': geo['country'],
                'lat': geo['lat'],
                'lng': geo['lng'],
                'count': 0,
                'max_severity': 'LOW',
                'timestamp': row.analyzed_at.isoformat()
            }
        
        location_counts[key]['count'] += 1
        
        # Update max severity
        if row.severity == 'CRITICAL':
            location_counts[key]['max_severity'] = 'CRITICAL'
        elif row.severity == 'HIGH' and location_counts[key]['max_severity'] != 'CRITICAL':
            location_counts[key]['max_severity'] = 'HIGH'
        elif row.severity == 'MEDIUM' and location_counts[key]['max_severity'] not in ['CRITICAL', 'HIGH']:
            location_counts[key]['max_severity'] = 'MEDIUM'
    
    attacks = []
    for loc in location_counts.values():
        attacks.append({
            'id': loc['id'],
            'lat': loc['lat'],
            'lng': loc['lng'],
            'city': loc['city'],
            'country': loc['country'],
            'severity': loc['max_severity'],
            'count': loc['count'],
            'timestamp': loc['timestamp']
        })
    
    return {"attacks": attacks, "period": f"{hours} hours"}


@router.get("/activity-heatmap")
async def get_activity_heatmap(
    days: int = Query(7, ge=1, le=30, description="Days to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user),
):
    """
    Get hourly activity distribution
    Returns count of threats per hour of day
    """
    cutoff_time = datetime.utcnow() - timedelta(days=days)

    # BUG-11 + BUG-24 fix: admins see all, SO sees org-wide, users see own only
    is_privileged = current_user.is_admin() or current_user.is_security_officer()

    base_conditions = [
        EmailAnalysis.analyzed_at >= cutoff_time,
        EmailAnalysis.risk_score >= 25
    ]

    if is_privileged:
        if not current_user.is_admin() and current_user.organization_id:
            base_conditions.append(
                EmailAnalysis.user_id.in_(
                    select(User.id).where(User.organization_id == current_user.organization_id)
                )
            )
    else:
        base_conditions.append(EmailAnalysis.user_id == current_user.id)

    # Query for hourly distribution
    query = select(
        func.extract('hour', EmailAnalysis.analyzed_at).label('hour'),
        func.count(EmailAnalysis.id).label('count')
    ).where(
        and_(*base_conditions)
    ).group_by(
        func.extract('hour', EmailAnalysis.analyzed_at)
    ).order_by(
        func.extract('hour', EmailAnalysis.analyzed_at)
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    # Create 24-hour array
    hourly_data = {i: 0 for i in range(24)}
    for row in rows:
        hour = int(row.hour)
        hourly_data[hour] = int(row.count)
    
    data = []
    for hour in range(24):
        data.append({
            "hour": f"{hour:02d}:00",
            "count": hourly_data[hour]
        })
    
    return {"data": data, "period": f"{days} days"}


@router.get("/risk-timeline")
async def get_risk_timeline(
    days: int = Query(14, ge=1, le=90, description="Days to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user),
):
    """
    Get risk score timeline
    Returns daily average and max risk scores
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # BUG-11 + BUG-24 fix: admins see all, SO sees org-wide, users see own only
    is_privileged = current_user.is_admin() or current_user.is_security_officer()

    base_conditions = [
        EmailAnalysis.analyzed_at >= start_date,
        EmailAnalysis.analyzed_at <= end_date
    ]

    if is_privileged:
        if not current_user.is_admin() and current_user.organization_id:
            base_conditions.append(
                EmailAnalysis.user_id.in_(
                    select(User.id).where(User.organization_id == current_user.organization_id)
                )
            )
    else:
        base_conditions.append(EmailAnalysis.user_id == current_user.id)

    # Query for daily risk scores
    query = select(
        func.date(EmailAnalysis.analyzed_at).label('date'),
        func.avg(EmailAnalysis.risk_score).label('avg_score'),
        func.max(EmailAnalysis.risk_score).label('max_score')
    ).where(
        and_(*base_conditions)
    ).group_by(
        func.date(EmailAnalysis.analyzed_at)
    ).order_by(
        func.date(EmailAnalysis.analyzed_at)
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    data = []
    for row in rows:
        data.append({
            "timestamp": row.date.strftime('%d.%m') if row.date else '',
            "score": float(row.max_score or 0),
            "average": float(row.avg_score or 0),
        })
    
    return {"data": data, "period": f"{days} days"}


@router.get("/threat-details/{date}")
async def get_threat_details(
    date: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user),
):
    """
    Get detailed threat information for a specific date
    Used for drill-down functionality
    """
    try:
        target_date = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}

    # BUG-11 + BUG-24 fix: admins see org-wide data, regular users see only their own
    is_privileged = current_user.is_admin() or current_user.is_security_officer()

    base_conditions = [
        func.date(EmailAnalysis.analyzed_at) == target_date,
        EmailAnalysis.risk_score >= 25
    ]

    if is_privileged:
        # Security officers: scope to their own organization if not admin
        if not current_user.is_admin() and current_user.organization_id:
            base_conditions.append(
                EmailAnalysis.user_id.in_(
                    select(User.id).where(User.organization_id == current_user.organization_id)
                )
            )
    else:
        # Regular users: their own data only
        base_conditions.append(EmailAnalysis.user_id == current_user.id)

    # Query threats for the specific date
    query = select(EmailAnalysis).where(
        and_(*base_conditions)
    ).order_by(
        desc(EmailAnalysis.risk_score)
    ).limit(100)
    
    result = await db.execute(query)
    threats = result.scalars().all()
    
    data = []
    for threat in threats:
        data.append({
            "id": threat.id,
            "from_address": threat.from_address,
            "to_address": threat.to_address,
            "subject": threat.subject,
            "risk_score": threat.risk_score,
            "status": threat.status,
            "analyzed_at": threat.analyzed_at.isoformat(),
        })
    
    return {
        "date": date,
        "total_threats": len(data),
        "threats": data
    }
