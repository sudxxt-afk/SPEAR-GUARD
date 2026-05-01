from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
from datetime import datetime
import logging

from database import TrustedRegistry
from schemas.registry import (
    RegistryCreate,
    RegistryUpdate,
    RegistryApprove,
    RegistryQuarantine,
    RegistryStats,
    RegistryStatus
)
from auth.permissions import CurrentUser

logger = logging.getLogger(__name__)


class RegistryService:
    """Service for managing trusted registry"""

    @staticmethod
    async def get_all(
        db: AsyncSession,
        page: int = 1,
        per_page: int = 20,
        trust_level: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        is_verified: Optional[bool] = None
    ) -> Tuple[List[TrustedRegistry], int]:
        """
        Get all registry entries with filtering and pagination
        """
        query = select(TrustedRegistry)

        # Apply filters
        filters = []
        if trust_level is not None:
            filters.append(TrustedRegistry.trust_level == trust_level)
        if status:
            if status == RegistryStatus.ACTIVE:
                filters.append(TrustedRegistry.is_active == True)
            elif status == RegistryStatus.QUARANTINE:
                filters.append(TrustedRegistry.is_active == False)
            elif status == RegistryStatus.PENDING:
                filters.append(and_(
                    TrustedRegistry.is_verified == False,
                    TrustedRegistry.approved_by.is_(None)
                ))
        if is_verified is not None:
            filters.append(TrustedRegistry.is_verified == is_verified)
        if search:
            search_filter = or_(
                TrustedRegistry.email_address.ilike(f"%{search}%"),
                TrustedRegistry.domain.ilike(f"%{search}%"),
                TrustedRegistry.organization_name.ilike(f"%{search}%")
            )
            filters.append(search_filter)

        if filters:
            query = query.where(and_(*filters))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        result = await db.execute(count_query)
        total = result.scalar()

        # Apply pagination
        query = query.offset((page - 1) * per_page).limit(per_page)
        query = query.order_by(TrustedRegistry.created_at.desc())

        # Execute query
        result = await db.execute(query)
        items = result.scalars().all()

        return items, total

    @staticmethod
    async def get_by_email(
        db: AsyncSession,
        email: str
    ) -> Optional[TrustedRegistry]:
        """Get registry entry by email address"""
        query = select(TrustedRegistry).where(
            TrustedRegistry.email_address == email.lower()
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        registry_id: int
    ) -> Optional[TrustedRegistry]:
        """Get registry entry by ID"""
        query = select(TrustedRegistry).where(TrustedRegistry.id == registry_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession,
        data: RegistryCreate,
        current_user: CurrentUser
    ) -> TrustedRegistry:
        """
        Create new registry entry
        Regular users create pending entries, security officers can create verified ones
        """
        # Check if email already exists
        existing = await RegistryService.get_by_email(db, data.email_address)
        if existing:
            raise ValueError(f"Email {data.email_address} already exists in registry")

        # Determine status based on user role
        is_verified = current_user.is_security_officer()
        status = "active" if is_verified else "pending"

        # Create new entry
        new_entry = TrustedRegistry(
            email_address=data.email_address.lower(),
            domain=data.domain.lower(),
            organization_name=data.organization_name,
            trust_level=data.trust_level.value,
            added_by=current_user.id,
            is_verified=is_verified,  # Auto-verify for security officers
            approved_by=current_user.id if is_verified else None,
            is_active=True,
            status=status,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(new_entry)
        await db.commit()
        await db.refresh(new_entry)

        logger.info(
            f"Registry entry created: {data.email_address} by user {current_user.id} "
            f"(verified: {new_entry.is_verified})"
        )

        return new_entry

    @staticmethod
    async def update(
        db: AsyncSession,
        email: str,
        data: RegistryUpdate,
        current_user: CurrentUser
    ) -> Optional[TrustedRegistry]:
        """Update registry entry"""
        entry = await RegistryService.get_by_email(db, email)
        if not entry:
            return None

        # Update fields
        if data.organization_name is not None:
            entry.organization_name = data.organization_name
        if data.trust_level is not None:
            entry.trust_level = data.trust_level.value
        if data.is_active is not None:
            entry.is_active = data.is_active

        entry.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(entry)

        logger.info(f"Registry entry updated: {email} by user {current_user.id}")

        return entry

    @staticmethod
    async def delete(
        db: AsyncSession,
        email: str,
        current_user: CurrentUser
    ) -> bool:
        """
        Delete (deactivate) registry entry
        """
        entry = await RegistryService.get_by_email(db, email)
        if not entry:
            return False

        # Soft delete - just deactivate
        entry.is_active = False
        entry.updated_at = datetime.utcnow()

        await db.commit()

        logger.info(f"Registry entry deleted: {email} by user {current_user.id}")

        return True

    @staticmethod
    async def get_pending(
        db: AsyncSession,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[TrustedRegistry], int]:
        """Get pending registry entries (not yet approved)"""
        query = select(TrustedRegistry).where(
            and_(
                TrustedRegistry.is_verified == False,
                TrustedRegistry.approved_by.is_(None),
                TrustedRegistry.is_active == True
            )
        )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        result = await db.execute(count_query)
        total = result.scalar()

        # Apply pagination
        query = query.offset((page - 1) * per_page).limit(per_page)
        query = query.order_by(TrustedRegistry.created_at.desc())

        result = await db.execute(query)
        items = result.scalars().all()

        return items, total

    @staticmethod
    async def approve(
        db: AsyncSession,
        email: str,
        data: RegistryApprove,
        current_user: CurrentUser
    ) -> Optional[TrustedRegistry]:
        """Approve pending registry entry"""
        entry = await RegistryService.get_by_email(db, email)
        if not entry:
            return None

        # Update entry
        entry.is_verified = True
        entry.approved_by = current_user.id
        entry.trust_level = data.approved_trust_level.value
        entry.is_active = True
        entry.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(entry)

        logger.info(
            f"Registry entry approved: {email} by user {current_user.id} "
            f"with trust level {data.approved_trust_level}"
        )

        return entry

    @staticmethod
    async def quarantine(
        db: AsyncSession,
        email: str,
        data: RegistryQuarantine,
        current_user: CurrentUser
    ) -> Optional[TrustedRegistry]:
        """Put registry entry into quarantine"""
        entry = await RegistryService.get_by_email(db, email)
        if not entry:
            return None

        # Deactivate entry
        entry.is_active = False
        entry.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(entry)

        logger.warning(
            f"Registry entry quarantined: {email} by user {current_user.id}. "
            f"Reason: {data.reason}"
        )

        return entry

    @staticmethod
    async def get_stats(db: AsyncSession) -> RegistryStats:
        """Get registry statistics"""
        # Total entries
        total_query = select(func.count()).select_from(TrustedRegistry)
        result = await db.execute(total_query)
        total_entries = result.scalar()

        # Active entries
        active_query = select(func.count()).select_from(TrustedRegistry).where(
            TrustedRegistry.is_active == True
        )
        result = await db.execute(active_query)
        active_entries = result.scalar()

        # Pending entries
        pending_query = select(func.count()).select_from(TrustedRegistry).where(
            and_(
                TrustedRegistry.is_verified == False,
                TrustedRegistry.approved_by.is_(None)
            )
        )
        result = await db.execute(pending_query)
        pending_entries = result.scalar()

        # Quarantine entries
        quarantine_entries = total_entries - active_entries

        # Verified/Unverified
        verified_query = select(func.count()).select_from(TrustedRegistry).where(
            TrustedRegistry.is_verified == True
        )
        result = await db.execute(verified_query)
        verified_count = result.scalar()
        unverified_count = total_entries - verified_count

        # By trust level
        by_trust_level = {}
        for level in [1, 2, 3, 4]:
            level_query = select(func.count()).select_from(TrustedRegistry).where(
                TrustedRegistry.trust_level == level
            )
            result = await db.execute(level_query)
            by_trust_level[level] = result.scalar()

        return RegistryStats(
            total_entries=total_entries,
            active_entries=active_entries,
            pending_entries=pending_entries,
            quarantine_entries=quarantine_entries,
            by_trust_level=by_trust_level,
            verified_count=verified_count,
            unverified_count=unverified_count
        )

    @staticmethod
    async def increment_email_count(
        db: AsyncSession,
        email: str
    ) -> None:
        """Increment email count for registry entry"""
        entry = await RegistryService.get_by_email(db, email)
        if entry:
            entry.total_emails += 1
            entry.last_email_at = datetime.utcnow()
            entry.updated_at = datetime.utcnow()
            await db.commit()
