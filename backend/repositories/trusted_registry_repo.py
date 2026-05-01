from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from database import TrustedRegistry

class TrustedRegistryRepository(BaseRepository[TrustedRegistry]):
    """
    Repository for accessing Trusted Registry
    """
    def __init__(self, db: AsyncSession):
        super().__init__(TrustedRegistry, db)

    async def get_by_email(self, email: str) -> Optional[TrustedRegistry]:
        stmt = select(self.model).where(
            and_(
                self.model.email_address == email,
                self.model.is_active == True,
                self.model.status == "active"
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
