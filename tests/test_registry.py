"""
Unit tests for Trusted Registry Service

Tests:
- Add/remove trusted senders
- Trust level management
- Organization scoping
- Email lookup and verification
"""

import pytest
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy.ext.asyncio import AsyncSession


class TestRegistryAddSender:
    """Test adding senders to trusted registry."""

    @pytest.mark.asyncio
    async def test_add_trusted_sender(self, test_db: AsyncSession, test_user, test_organization):
        """Should add new sender to registry."""
        from services.registry_service import RegistryService
        
        service = RegistryService(test_db)
        
        result = await service.add_sender(
            email="partner@partner.gov.ru",
            domain="partner.gov.ru",
            organization_name="Partner Org",
            trust_level=1,
            added_by=test_user.id,
            organization_id=test_organization.id
        )
        
        assert result.email_address == "partner@partner.gov.ru"
        assert result.is_active is True
        assert result.trust_level == 1

    @pytest.mark.asyncio
    async def test_add_duplicate_email_fails(self, test_db: AsyncSession, test_user, test_organization, test_trusted_sender):
        """Adding duplicate email should fail."""
        from services.registry_service import RegistryService
        from sqlalchemy.exc import IntegrityError
        
        service = RegistryService(test_db)
        
        # Try to add same email again
        with pytest.raises(Exception):
            await service.add_sender(
                email=test_trusted_sender.email_address,
                domain=test_trusted_sender.domain,
                organization_name="Duplicate Org",
                trust_level=2,
                added_by=test_user.id,
                organization_id=test_organization.id
            )


class TestRegistryLookup:
    """Test looking up senders in registry."""

    @pytest.mark.asyncio
    async def test_find_existing_sender(self, test_db: AsyncSession, test_trusted_sender):
        """Should find existing sender in registry."""
        from services.registry_service import RegistryService
        
        service = RegistryService(test_db)
        
        result = await service.find_by_email(test_trusted_sender.email_address)
        
        assert result is not None
        assert result.email_address == test_trusted_sender.email_address

    @pytest.mark.asyncio
    async def test_find_nonexistent_sender_returns_none(self, test_db: AsyncSession):
        """Nonexistent sender should return None."""
        from services.registry_service import RegistryService
        
        service = RegistryService(test_db)
        
        result = await service.find_by_email("unknown@example.com")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_domain(self, test_db: AsyncSession, test_trusted_sender):
        """Should find sender by domain."""
        from services.registry_service import RegistryService
        
        service = RegistryService(test_db)
        
        results = await service.find_by_domain(test_trusted_sender.domain)
        
        assert len(results) > 0
        assert any(r.domain == test_trusted_sender.domain for r in results)


class TestTrustLevelManagement:
    """Test trust level updates."""

    @pytest.mark.asyncio
    async def test_update_trust_level(self, test_db: AsyncSession, test_trusted_sender):
        """Should update sender's trust level."""
        from services.registry_service import RegistryService
        
        service = RegistryService(test_db)
        
        await service.update_trust_level(
            test_trusted_sender.id,
            new_level=2
        )
        
        await test_db.refresh(test_trusted_sender)
        
        assert test_trusted_sender.trust_level == 2

    @pytest.mark.asyncio
    async def test_verify_sender(self, test_db: AsyncSession, test_trusted_sender):
        """Should mark sender as verified."""
        from services.registry_service import RegistryService
        
        service = RegistryService(test_db)
        
        await service.verify_sender(
            test_trusted_sender.id,
            approved_by=1  # admin user
        )
        
        await test_db.refresh(test_trusted_sender)
        
        assert test_trusted_sender.is_verified is True
        assert test_trusted_sender.approved_by == 1

    @pytest.mark.asyncio
    async def test_deactivate_sender(self, test_db: AsyncSession, test_trusted_sender):
        """Should deactivate sender."""
        from services.registry_service import RegistryService
        
        service = RegistryService(test_db)
        
        await service.deactivate_sender(test_trusted_sender.id)
        
        await test_db.refresh(test_trusted_sender)
        
        assert test_trusted_sender.is_active is False


class TestOrganizationScoping:
    """Test organization-based data isolation."""

    @pytest.mark.asyncio
    async def test_list_org_senders_only(self, test_db: AsyncSession, test_organization, test_trusted_sender):
        """Should only list senders from user's organization."""
        from services.registry_service import RegistryService
        
        service = RegistryService(test_db)
        
        results = await service.list_senders(
            organization_id=test_organization.id
        )
        
        # All results should belong to this organization
        for r in results:
            assert r.organization_id == test_organization.id

    @pytest.mark.asyncio
    async def test_global_sender_visible_to_all(self, test_db: AsyncSession):
        """Global sender (no org) should be visible to all."""
        from services.registry_service import RegistryService
        from database import TrustedRegistry
        
        # Add global sender
        global_sender = TrustedRegistry(
            organization_id=None,  # Global
            email_address="government@gov.ru",
            domain="gov.ru",
            organization_name="Government",
            trust_level=1,
            is_active=True,
            is_verified=True
        )
        test_db.add(global_sender)
        await test_db.flush()
        
        service = RegistryService(test_db)
        
        # Should be found when no org filter
        result = await service.find_by_email("government@gov.ru")
        
        assert result is not None


class TestRegistryStats:
    """Test registry statistics."""

    @pytest.mark.asyncio
    async def test_count_by_trust_level(self, test_db: AsyncSession, test_trusted_sender):
        """Should count senders by trust level."""
        from services.registry_service import RegistryService
        
        service = RegistryService(test_db)
        
        stats = await service.get_stats()
        
        assert "total" in stats
        assert stats["total"] >= 1

    @pytest.mark.asyncio
    async def test_recently_active_senders(self, test_db: AsyncSession, test_trusted_sender):
        """Should find recently active senders."""
        from services.registry_service import RegistryService
        
        service = RegistryService(test_db)
        
        results = await service.get_recently_active(limit=10)
        
        # Should include our test sender
        assert len(results) >= 1