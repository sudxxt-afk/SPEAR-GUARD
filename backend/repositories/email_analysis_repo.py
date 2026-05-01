from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import select, func, and_, desc, Select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from database import EmailAnalysis

class EmailAnalysisRepository(BaseRepository[EmailAnalysis]):
    """
    Repository for accessing email analysis records and statistics
    """
    def __init__(self, db: AsyncSession):
        super().__init__(EmailAnalysis, db)

    async def get_by_message_id(self, message_id: str) -> Optional[EmailAnalysis]:
        stmt = select(self.model).where(self.model.message_id == message_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_recent_by_sender(self, from_address: str, days: int = 7, limit: int = 50) -> List[EmailAnalysis]:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        stmt = select(self.model).where(
            and_(
                self.model.from_address == from_address,
                self.model.analyzed_at >= cutoff_date
            )
        ).order_by(desc(self.model.analyzed_at)).limit(limit)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_daily_volumes(self, from_address: str, days: int = 30) -> List[Tuple[datetime, int]]:
        """
        Get daily email count for a sender
        Used for Z-Score analysis
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        stmt = select(
            func.date(self.model.analyzed_at).label('date'),
            func.count(self.model.id).label('daily_count')
        ).where(
            and_(
                self.model.from_address == from_address,
                self.model.analyzed_at >= cutoff_date
            )
        ).group_by(
            func.date(self.model.analyzed_at)
        )
        
        result = await self.db.execute(stmt)
        # Returns list of (date, count) tuples
        return [(r.date, r.daily_count) for r in result.all()]

    async def count_recent_emails(self, from_address: str, hours: int = 24) -> int:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        stmt = select(func.count(self.model.id)).where(
            and_(
                self.model.from_address == from_address,
                self.model.analyzed_at >= cutoff
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def get_sender_reputation_stats(self, from_address: str) -> dict:
        """
        Get long-term reputation stats:
        - Total emails
        - Average risk score
        - Count of high-risk emails
        """
        stmt = select(
            func.count(self.model.id).label("total"),
            func.avg(self.model.risk_score).label("avg_risk"),
            func.count(self.model.id).filter(self.model.risk_score > 70).label("high_risk_count")
        ).where(
            self.model.from_address == from_address
        )
        
        result = await self.db.execute(stmt)
        row = result.one()
        
        return {
            "total_emails": row.total or 0,
            "avg_risk": float(row.avg_risk or 0.0),
            "high_risk_count": row.high_risk_count or 0
        }
